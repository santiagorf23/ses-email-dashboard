import logging
import smtplib
import json
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime, timezone
from typing import Optional
import httpx

logger = logging.getLogger(__name__)

SLACK_WEBHOOK_URL = "https://hooks.slack.com/services/YOUR/WEBHOOK/URL"


async def send_slack_notification(
    webhook_url: str,
    title: str,
    message: str,
    severity: str,
    alert_type: str,
    domain: Optional[str] = None
) -> bool:
    """Send alert notification to Slack."""
    try:
        # Color based on severity
        color_map = {
            "critical": "#dc3545",
            "warning": "#ffc107",
            "info": "#17a2b8"
        }
        color = color_map.get(severity, "#6c757d")
        
        # Emoji based on severity
        emoji_map = {
            "critical": "🚨",
            "warning": "⚠️",
            "info": "ℹ️"
        }
        emoji = emoji_map.get(severity, "📢")
        
        # Build Slack message
        slack_message = {
            "attachments": [
                {
                    "color": color,
                    "blocks": [
                        {
                            "type": "header",
                            "text": {
                                "type": "plain_text",
                                "text": f"{emoji} {title}",
                                "emoji": True
                            }
                        },
                        {
                            "type": "section",
                            "text": {
                                "type": "mrkdwn",
                                "text": message
                            }
                        },
                        {
                            "type": "context",
                            "elements": [
                                {
                                    "type": "mrkdwn",
                                    "text": f"Tipo: `{alert_type}` | Severidad: `{severity}` | Dominio: `{domain or 'N/A'}`"
                                }
                            ]
                        }
                    ]
                }
            ]
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                webhook_url,
                json=slack_message,
                timeout=10.0
            )
            
            if response.status_code == 200:
                logger.info(f"Slack notification sent: {title}")
                return True
            else:
                logger.error(f"Slack notification failed: {response.status_code} - {response.text}")
                return False
                
    except Exception as e:
        logger.error(f"Slack notification error: {e}")
        return False


def send_email_notification(
    smtp_host: str,
    smtp_port: int,
    smtp_user: str,
    smtp_password: str,
    from_email: str,
    to_email: str,
    title: str,
    message: str,
    severity: str,
    alert_type: str,
    domain: Optional[str] = None
) -> bool:
    """Send alert notification via email."""
    try:
        # Color based on severity
        color_map = {
            "critical": "#dc3545",
            "warning": "#ffc107",
            "info": "#17a2b8"
        }
        color = color_map.get(severity, "#6c757d")
        
        # Build HTML email
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                .header {{ background-color: {color}; color: white; padding: 20px; border-radius: 8px 8px 0 0; }}
                .content {{ background-color: #f8f9fa; padding: 20px; border: 1px solid #dee2e6; }}
                .footer {{ background-color: #e9ecef; padding: 10px 20px; border-radius: 0 0 8px 8px; font-size: 12px; color: #6c757d; }}
                .badge {{ display: inline-block; padding: 4px 8px; border-radius: 4px; font-size: 12px; font-weight: bold; color: white; background-color: {color}; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h2 style="margin:0">🔔 {title}</h2>
                </div>
                <div class="content">
                    <p>{message}</p>
                    <p><strong>Tipo de alerta:</strong> {alert_type}</p>
                    <p><strong>Severidad:</strong> <span class="badge">{severity.upper()}</span></p>
                    {f'<p><strong>Dominio:</strong> {domain}</p>' if domain else ''}
                    <p><strong>Fecha:</strong> {datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")}</p>
                </div>
                <div class="footer">
                    SES Dashboard - Notificación de Deliverability
                </div>
            </div>
        </body>
        </html>
        """
        
        # Create message
        msg = MIMEMultipart("alternative")
        msg["Subject"] = f"[SES Dashboard] {severity.upper()}: {title}"
        msg["From"] = from_email
        msg["To"] = to_email
        
        # Attach HTML content
        msg.attach(MIMEText(html_content, "html"))
        
        # Send email
        with smtplib.SMTP(smtp_host, smtp_port) as server:
            server.starttls()
            server.login(smtp_user, smtp_password)
            server.sendmail(from_email, to_email, msg.as_string())
        
        logger.info(f"Email notification sent to {to_email}: {title}")
        return True
        
    except Exception as e:
        logger.error(f"Email notification error: {e}")
        return False


async def notify_alert_created(
    alert_config: dict,
    alert: dict,
    tenant_config: dict
) -> None:
    """Send notification for a new alert."""
    title = alert.get("title", "Alerta de Deliverability")
    message = alert.get("message", "Se ha detectado un problema de deliverability")
    severity = alert.get("severity", "warning")
    alert_type = alert.get("alert_type", "unknown")
    domain = alert.get("domain")
    
    # Send Slack notification if configured
    slack_webhook = tenant_config.get("slack_webhook_url")
    if slack_webhook:
        await send_slack_notification(
            webhook_url=slack_webhook,
            title=title,
            message=message,
            severity=severity,
            alert_type=alert_type,
            domain=domain
        )
    
    # Send email notification if configured
    email_config = tenant_config.get("email_notification")
    if email_config:
        send_email_notification(
            smtp_host=email_config.get("smtp_host"),
            smtp_port=email_config.get("smtp_port", 587),
            smtp_user=email_config.get("smtp_user"),
            smtp_password=email_config.get("smtp_password"),
            from_email=email_config.get("from_email"),
            to_email=email_config.get("to_email"),
            title=title,
            message=message,
            severity=severity,
            alert_type=alert_type,
            domain=domain
        )
