import logging
import csv
import io
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, Query, HTTPException
from fastapi.responses import StreamingResponse
from db.database import get_conn
from routers.auth import get_current_user
from routers.reports import (
    _get_domain_report_data,
    _get_trend_data,
    _get_overall_stats
)

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/csv")
async def export_report_csv(
    days: int = Query(30, ge=1, le=365),
    conn=Depends(get_conn),
    current_user: dict = Depends(get_current_user)
):
    """Export deliverability report as CSV."""
    tenant_id = current_user["tenant_id"]
    
    # Get report data
    overall = await _get_overall_stats(conn, tenant_id, days)
    domains = await _get_domain_report_data(conn, tenant_id, days)
    trends = await _get_trend_data(conn, tenant_id, days)
    
    # Create CSV content
    output = io.StringIO()
    writer = csv.writer(output)
    
    # Header
    writer.writerow(["SES Dashboard - Reporte de Deliverability"])
    writer.writerow([f"Periodo: {days} dias", f"Generado: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}"])
    writer.writerow([])
    
    # Overall stats
    writer.writerow(["RESUMEN GENERAL"])
    writer.writerow(["Metrica", "Valor"])
    writer.writerow(["Total Enviados", overall["total_sent"]])
    writer.writerow(["Total Entregados", overall["total_delivered"]])
    writer.writerow(["Total Rebotados", overall["total_bounced"]])
    writer.writerow(["Total Quejas", overall["total_complaints"]])
    writer.writerow(["Total Abiertos", overall["total_opened"]])
    writer.writerow(["Tasa de Entrega", f"{overall['delivery_rate']}%"])
    writer.writerow(["Tasa de Bounce", f"{overall['bounce_rate']}%"])
    writer.writerow(["Tasa de Quejas", f"{overall['complaint_rate']}%"])
    writer.writerow(["Tasa de Apertura", f"{overall['open_rate']}%"])
    writer.writerow([])
    
    # Domain breakdown
    writer.writerow(["REPORTE POR DOMINIO"])
    writer.writerow(["Dominio", "Enviados", "Entregados", "Rebotados", "Quejas", "Abiertos", 
                     "Tasa Entrega", "Tasa Bounce", "Tasa Quejas", "Tasa Apertura", 
                     "Score Reputacion", "Nivel"])
    for d in domains:
        writer.writerow([
            d["domain"], d["total_sent"], d["total_delivered"], d["total_bounced"],
            d["total_complaints"], d["total_opened"], f"{d['delivery_rate']}%",
            f"{d['bounce_rate']}%", f"{d['complaint_rate']}%", f"{d['open_rate']}%",
            d["reputation_score"], d["reputation_label"]
        ])
    writer.writerow([])
    
    # Daily trends
    writer.writerow(["TENDENCIAS DIARIAS"])
    writer.writerow(["Fecha", "Enviados", "Entregados", "Rebotados", "Quejas", "Abiertos",
                     "Tasa Entrega", "Tasa Bounce", "Tasa Quejas"])
    for t in trends:
        writer.writerow([
            t["date"], t["sent"], t["delivered"], t["bounced"], t["complaints"],
            t["opened"], f"{t['delivery_rate']}%", f"{t['bounce_rate']}%", f"{t['complaint_rate']}%"
        ])
    
    # Generate filename
    filename = f"reporte_deliverability_{days}d_{datetime.now(timezone.utc).strftime('%Y%m%d')}.csv"
    
    # Return as streaming response
    output.seek(0)
    return StreamingResponse(
        io.BytesIO(output.getvalue().encode('utf-8-sig')),  # UTF-8 BOM for Excel compatibility
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'}
    )


@router.get("/pdf")
async def export_report_pdf(
    days: int = Query(30, ge=1, le=365),
    conn=Depends(get_conn),
    current_user: dict = Depends(get_current_user)
):
    """Export deliverability report as PDF."""
    tenant_id = current_user["tenant_id"]
    
    # Get report data
    overall = await _get_overall_stats(conn, tenant_id, days)
    domains = await _get_domain_report_data(conn, tenant_id, days)
    trends = await _get_trend_data(conn, tenant_id, days)
    
    # Generate HTML content for PDF
    html_content = _generate_pdf_html(overall, domains, trends, days)
    
    # Generate filename
    filename = f"reporte_deliverability_{days}d_{datetime.now(timezone.utc).strftime('%Y%m%d')}.html"
    
    # Return HTML that can be printed to PDF
    # For a real PDF generation, you'd use a library like weasyprint or reportlab
    return StreamingResponse(
        io.BytesIO(html_content.encode('utf-8')),
        media_type="text/html",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'}
    )


def _generate_pdf_html(overall: dict, domains: list, trends: list, days: int) -> str:
    """Generate HTML content for PDF report."""
    html = f"""<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <title>Reporte de Deliverability - SES Dashboard</title>
    <style>
        @page {{
            size: A4;
            margin: 20mm;
        }}
        body {{
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            line-height: 1.6;
            color: #333;
            max-width: 800px;
            margin: 0 auto;
            padding: 20px;
        }}
        .header {{
            background: linear-gradient(135deg, #0d9488 0%, #14b8a6 100%);
            color: white;
            padding: 30px;
            border-radius: 10px;
            margin-bottom: 30px;
            text-align: center;
        }}
        .header h1 {{
            margin: 0;
            font-size: 28px;
            font-weight: 600;
        }}
        .header .subtitle {{
            margin-top: 10px;
            opacity: 0.9;
            font-size: 14px;
        }}
        .section {{
            background: #f8fafc;
            border: 1px solid #e2e8f0;
            border-radius: 8px;
            padding: 20px;
            margin-bottom: 20px;
        }}
        .section h2 {{
            color: #0d9488;
            margin-top: 0;
            font-size: 18px;
            border-bottom: 2px solid #0d9488;
            padding-bottom: 10px;
        }}
        .stats-grid {{
            display: grid;
            grid-template-columns: repeat(2, 1fr);
            gap: 15px;
        }}
        .stat-card {{
            background: white;
            border: 1px solid #e2e8f0;
            border-radius: 6px;
            padding: 15px;
            text-align: center;
        }}
        .stat-card .value {{
            font-size: 24px;
            font-weight: 700;
            color: #0d9488;
        }}
        .stat-card .label {{
            font-size: 12px;
            color: #64748b;
            margin-top: 5px;
        }}
        table {{
            width: 100%;
            border-collapse: collapse;
            margin-top: 15px;
            font-size: 12px;
        }}
        th, td {{
            padding: 10px 8px;
            text-align: left;
            border-bottom: 1px solid #e2e8f0;
        }}
        th {{
            background: #0d9488;
            color: white;
            font-weight: 600;
        }}
        tr:nth-child(even) {{
            background: #f1f5f9;
        }}
        .reputation-excellent {{ color: #10b981; font-weight: bold; }}
        .reputation-good {{ color: #3b82f6; font-weight: bold; }}
        .reputation-fair {{ color: #f59e0b; font-weight: bold; }}
        .reputation-poor {{ color: #ef4444; font-weight: bold; }}
        .footer {{
            text-align: center;
            margin-top: 30px;
            padding-top: 20px;
            border-top: 1px solid #e2e8f0;
            color: #64748b;
            font-size: 12px;
        }}
        @media print {{
            body {{
                padding: 0;
            }}
            .section {{
                break-inside: avoid;
            }}
        }}
    </style>
</head>
<body>
    <div class="header">
        <h1>📧 Reporte de Deliverability</h1>
        <div class="subtitle">SES Dashboard | Periodo: {days} dias | Generado: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}</div>
    </div>
    
    <div class="section">
        <h2>📊 Resumen General</h2>
        <div class="stats-grid">
            <div class="stat-card">
                <div class="value">{overall['total_sent']}</div>
                <div class="label">Total Enviados</div>
            </div>
            <div class="stat-card">
                <div class="value">{overall['delivery_rate']}%</div>
                <div class="label">Tasa de Entrega</div>
            </div>
            <div class="stat-card">
                <div class="value">{overall['bounce_rate']}%</div>
                <div class="label">Tasa de Bounce</div>
            </div>
            <div class="stat-card">
                <div class="value">{overall['complaint_rate']}%</div>
                <div class="label">Tasa de Quejas</div>
            </div>
            <div class="stat-card">
                <div class="value">{overall['open_rate']}%</div>
                <div class="label">Tasa de Apertura</div>
            </div>
        </div>
    </div>
    
    <div class="section">
        <h2>🌐 Reporte por Dominio</h2>
        <table>
            <thead>
                <tr>
                    <th>Dominio</th>
                    <th>Enviados</th>
                    <th>Entrega</th>
                    <th>Bounce</th>
                    <th>Quejas</th>
                    <th>Apertura</th>
                    <th>Reputacion</th>
                </tr>
            </thead>
            <tbody>
"""
    
    for d in domains:
        html += f"""                <tr>
                    <td>{d['domain']}</td>
                    <td>{d['total_sent']}</td>
                    <td>{d['delivery_rate']}%</td>
                    <td>{d['bounce_rate']}%</td>
                    <td>{d['complaint_rate']}%</td>
                    <td>{d['open_rate']}%</td>
                    <td class="reputation-{d['reputation_label']}">{d['reputation_score']}/100</td>
                </tr>
"""
    
    html += """            </tbody>
        </table>
    </div>
    
    <div class="section">
        <h2>📈 Tendencias Diarias</h2>
        <table>
            <thead>
                <tr>
                    <th>Fecha</th>
                    <th>Enviados</th>
                    <th>Entregados</th>
                    <th>Rebotados</th>
                    <th>Quejas</th>
                    <th>Abiertos</th>
                </tr>
            </thead>
            <tbody>
"""
    
    for t in trends[-30:]:  # Last 30 days for PDF
        html += f"""                <tr>
                    <td>{t['date']}</td>
                    <td>{t['sent']}</td>
                    <td>{t['delivered']}</td>
                    <td>{t['bounced']}</td>
                    <td>{t['complaints']}</td>
                    <td>{t['opened']}</td>
                </tr>
"""
    
    html += """            </tbody>
        </table>
    </div>
    
    <div class="footer">
        <p>SES Dashboard - Reporte de Deliverability</p>
        <p>Para imprimir como PDF: Ctrl+P (Cmd+P en Mac) → Seleccionar "Guardar como PDF"</p>
    </div>
</body>
</html>"""
    
    return html
