"""
MailPulse — SES Dashboard
services/report_scheduler.py

APScheduler-based periodic report generation and email sending.
Runs every 30 minutes, generates PDF reports for tenants with scheduled reports enabled.
"""
import logging
from datetime import datetime, timezone
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from services.pdf_generator import generate_report_pdf
from services.email_sender import send_report_email

logger = logging.getLogger(__name__)

scheduler = AsyncIOScheduler()


async def generate_and_send_reports():
    """Generate and send reports for all eligible tenants."""
    from db.database import get_pool

    pool = get_pool()
    if not pool:
        return

    try:
        async with pool.acquire() as conn:
            # Find tenants with scheduled reports enabled
            rows = await conn.fetch("""
                SELECT t.id, t.slug, t.name, t.notification_config,
                    rc.report_type, rc.frequency_hours, rc.is_enabled
                FROM tenants t
                JOIN report_config rc ON t.id = rc.tenant_id
                WHERE rc.is_enabled = TRUE
                AND (rc.last_sent_at IS NULL 
                     OR rc.last_sent_at < NOW() - (rc.frequency_hours || ' hours')::interval)
            """)

            for row in rows:
                tenant_id = row["id"]
                notification_config = row["notification_config"]
                if isinstance(notification_config, str):
                    import json
                    notification_config = json.loads(notification_config)

                to_email = (
                    notification_config.get("notify_email")
                    or notification_config.get("email_to")
                )
                if not to_email:
                    logger.warning("No email configured for tenant %d, skipping", tenant_id)
                    continue

                smtp_config = {
                    "host": notification_config.get("smtp_host", "smtp.gmail.com"),
                    "port": notification_config.get("smtp_port", 587),
                    "user": notification_config.get("smtp_user"),
                    "password": notification_config.get("smtp_password"),
                    "from_email": notification_config.get("from_email"),
                }

                days = 30 if row["report_type"] == "monthly" else 7

                # Generate report data
                overall = await _get_overall_stats_for_tenant(conn, tenant_id, days)
                domains = await _get_domain_report_for_tenant(conn, tenant_id, days)
                trends = await _get_trends_for_tenant(conn, tenant_id, days)

                report_data = {
                    "period_days": days,
                    "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
                    **overall,
                    "domains": domains,
                    "trends": [{"date": str(t["date"]), **t} for t in trends],
                }

                # Generate PDF
                pdf_buffer = generate_report_pdf(report_data)
                pdf_bytes = pdf_buffer.read()

                # Send email
                subject = f"MailPulse Report - {row['name'] or row['slug']} ({days}d)"
                html_body = f"<h2>MailPulse Deliverability Report</h2><p>Periodo: {days} dias.</p><p>Ver PDF adjunto.</p>"

                sent = send_report_email(
                    to_email=to_email,
                    subject=subject,
                    html_body=html_body,
                    pdf_bytes=pdf_bytes,
                    pdf_filename=f"mailpulse-report-{days}d.pdf",
                    smtp_config=smtp_config,
                )

                # Update last_sent_at
                if sent:
                    await conn.execute(
                        "UPDATE report_config SET last_sent_at = NOW() WHERE tenant_id = $1",
                        tenant_id,
                    )
                    logger.info("Report sent for tenant %d", tenant_id)

    except Exception as e:
        logger.error("Report scheduler error: %s", e)


async def _get_overall_stats_for_tenant(conn, tenant_id: int, days: int) -> dict:
    row = await conn.fetchrow("""
        SELECT 
            COUNT(DISTINCT es.id) as total_sent,
            COUNT(DISTINCT CASE WHEN LOWER(ee.event_type) = 'delivery' THEN ee.email_send_id END) as total_delivered,
            COUNT(DISTINCT CASE WHEN LOWER(ee.event_type) = 'bounce' THEN ee.email_send_id END) as total_bounced,
            COUNT(DISTINCT CASE WHEN LOWER(ee.event_type) = 'complaint' THEN ee.email_send_id END) as total_complaints,
            COUNT(DISTINCT CASE WHEN LOWER(ee.event_type) = 'open' THEN ee.email_send_id END) as total_opened
        FROM email_send es
        LEFT JOIN email_events ee ON es.id = ee.email_send_id AND ee.tenant_id = $1
        WHERE es.tenant_id = $1 
        AND es.created_at >= NOW() - INTERVAL '1 day' * $2
    """, tenant_id, days)

    total_sent = row["total_sent"] or 0
    total_delivered = row["total_delivered"] or 0
    total_bounced = row["total_bounced"] or 0
    total_complaints = row["total_complaints"] or 0
    total_opened = row["total_opened"] or 0

    return {
        "total_sent": total_sent,
        "total_delivered": total_delivered,
        "total_bounced": total_bounced,
        "total_complaints": total_complaints,
        "total_opened": total_opened,
        "overall_delivery_rate": round((total_delivered / total_sent * 100) if total_sent > 0 else 0, 2),
        "overall_bounce_rate": round((total_bounced / total_sent * 100) if total_sent > 0 else 0, 2),
        "overall_complaint_rate": round((total_complaints / total_sent * 100) if total_sent > 0 else 0, 2),
        "overall_open_rate": round((total_opened / total_delivered * 100) if total_delivered > 0 else 0, 2),
    }


async def _get_domain_report_for_tenant(conn, tenant_id: int, days: int) -> list:
    rows = await conn.fetch("""
        SELECT 
            SPLIT_PART(es.email_from, '@', 2) as domain,
            COUNT(DISTINCT es.id) as total_sent,
            COUNT(DISTINCT CASE WHEN LOWER(ee.event_type) = 'delivery' THEN ee.email_send_id END) as total_delivered,
            COUNT(DISTINCT CASE WHEN LOWER(ee.event_type) = 'bounce' THEN ee.email_send_id END) as total_bounced,
            COUNT(DISTINCT CASE WHEN LOWER(ee.event_type) = 'complaint' THEN ee.email_send_id END) as total_complaints,
            COUNT(DISTINCT CASE WHEN LOWER(ee.event_type) = 'open' THEN ee.email_send_id END) as total_opened
        FROM email_send es
        LEFT JOIN email_events ee ON es.id = ee.email_send_id AND ee.tenant_id = $1
        WHERE es.tenant_id = $1 
        AND es.created_at >= NOW() - INTERVAL '1 day' * $2
        GROUP BY SPLIT_PART(es.email_from, '@', 2)
        ORDER BY total_sent DESC
    """, tenant_id, days)

    results = []
    for row in rows:
        d = dict(row)
        d_sent = d["total_sent"] or 0
        d_delivered = d["total_delivered"] or 0
        d_bounced = d["total_bounced"] or 0
        d_complaints = d["total_complaints"] or 0
        d_opened = d["total_opened"] or 0

        delivery_rate = (d_delivered / d_sent * 100) if d_sent > 0 else 0
        bounce_rate = (d_bounced / d_sent * 100) if d_sent > 0 else 0
        complaint_rate = (d_complaints / d_sent * 100) if d_sent > 0 else 0

        results.append({
            "domain": d["domain"],
            "total_sent": d_sent,
            "total_delivered": d_delivered,
            "total_bounced": d_bounced,
            "total_complaints": d_complaints,
            "total_opened": d_opened,
            "delivery_rate": round(delivery_rate, 2),
            "bounce_rate": round(bounce_rate, 2),
            "complaint_rate": round(complaint_rate, 2),
            "open_rate": round((d_opened / d_delivered * 100) if d_delivered > 0 else 0, 2),
            "reputation_score": 100,
            "reputation_label": "good",
        })

    return results


async def _get_trends_for_tenant(conn, tenant_id: int, days: int) -> list:
    rows = await conn.fetch("""
        SELECT 
            DATE(es.created_at) as date,
            COUNT(DISTINCT es.id) as sent,
            COUNT(DISTINCT CASE WHEN LOWER(ee.event_type) = 'delivery' THEN ee.email_send_id END) as delivered,
            COUNT(DISTINCT CASE WHEN LOWER(ee.event_type) = 'bounce' THEN ee.email_send_id END) as bounced,
            COUNT(DISTINCT CASE WHEN LOWER(ee.event_type) = 'complaint' THEN ee.email_send_id END) as complaints,
            COUNT(DISTINCT CASE WHEN LOWER(ee.event_type) = 'open' THEN ee.email_send_id END) as opened
        FROM email_send es
        LEFT JOIN email_events ee ON es.id = ee.email_send_id AND ee.tenant_id = $1
        WHERE es.tenant_id = $1 
        AND es.created_at >= NOW() - INTERVAL '1 day' * $2
        GROUP BY DATE(es.created_at)
        ORDER BY date ASC
    """, tenant_id, days)

    results = []
    for row in rows:
        t = dict(row)
        t_sent = t["sent"] or 0
        t_delivered = t["delivered"] or 0
        t_bounced = t["bounced"] or 0
        t_complaints = t["complaints"] or 0

        results.append({
            "date": str(t["date"]),
            "sent": t_sent,
            "delivered": t_delivered,
            "bounced": t_bounced,
            "complaints": t_complaints,
            "opened": t["opened"] or 0,
            "delivery_rate": round((t_delivered / t_sent * 100) if t_sent > 0 else 0, 2),
            "bounce_rate": round((t_bounced / t_sent * 100) if t_sent > 0 else 0, 2),
            "complaint_rate": round((t_complaints / t_sent * 100) if t_sent > 0 else 0, 2),
        })

    return results


def start_scheduler():
    """Start the report scheduler."""
    scheduler.add_job(
        generate_and_send_reports,
        "interval",
        minutes=30,
        id="report_scheduler",
        replace_existing=True,
    )
    scheduler.start()
    logger.info("Report scheduler started (every 30 min)")


def stop_scheduler():
    """Stop the report scheduler."""
    if scheduler.running:
        scheduler.shutdown()
        logger.info("Report scheduler stopped")
