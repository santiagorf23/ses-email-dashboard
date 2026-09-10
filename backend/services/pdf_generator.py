"""
MailPulse — SES Dashboard
services/pdf_generator.py

PDF report generation with WeasyPrint + Jinja2.
"""
import logging
from datetime import datetime, timezone
from io import BytesIO
from jinja2 import Environment, BaseLoader
from weasyprint import HTML

logger = logging.getLogger(__name__)

REPORT_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<style>
    * { margin: 0; padding: 0; box-sizing: border-box; }
    body { font-family: 'Segoe UI', Arial, sans-serif; color: #1a1a1a; font-size: 11px; line-height: 1.5; }
    .cover { text-align: center; padding: 60px 40px 40px; }
    .cover h1 { font-size: 28px; font-weight: 700; color: #0d9488; margin-bottom: 8px; }
    .cover .subtitle { font-size: 14px; color: #666; margin-bottom: 20px; }
    .cover .period { font-size: 12px; color: #999; }
    .cover .logo { font-size: 16px; font-weight: 600; color: #0d9488; margin-bottom: 30px; }
    .section { padding: 15px 40px; }
    .section-title { font-size: 14px; font-weight: 700; color: #0d9488; border-bottom: 2px solid #0d9488;
        padding-bottom: 4px; margin-bottom: 12px; }
    .kpi-grid { display: grid; grid-template-columns: repeat(4, 1fr); gap: 12px; margin-bottom: 20px; }
    .kpi-card { background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 8px; padding: 12px; text-align: center; }
    .kpi-value { font-size: 22px; font-weight: 700; color: #0d9488; }
    .kpi-label { font-size: 9px; color: #666; text-transform: uppercase; letter-spacing: 0.5px; margin-top: 2px; }
    table { width: 100%; border-collapse: collapse; margin-top: 10px; font-size: 10px; }
    th { background: #f1f5f9; text-align: left; padding: 6px 8px; font-weight: 600; color: #475569;
        border-bottom: 2px solid #e2e8f0; font-size: 9px; text-transform: uppercase; letter-spacing: 0.3px; }
    td { padding: 6px 8px; border-bottom: 1px solid #f1f5f9; }
    tr:hover td { background: #f8fafc; }
    .good { color: #16a34a; font-weight: 600; }
    .warn { color: #d97706; font-weight: 600; }
    .bad { color: #dc2626; font-weight: 600; }
    .footer { text-align: center; padding: 20px 40px; color: #999; font-size: 9px; border-top: 1px solid #e2e8f0; margin-top: 30px; }
    @page { size: A4; margin: 15mm; }
</style>
</head>
<body>
    <div class="cover">
        <div class="logo">MailPulse</div>
        <h1>Deliverability Report</h1>
        <div class="subtitle">Reporte de reputacion y entregabilidad SES</div>
        <div class="period">Periodo: {{ period_days }} dias | Generado: {{ generated_at }}</div>
    </div>

    <div class="section">
        <div class="section-title">Resumen General</div>
        <div class="kpi-grid">
            <div class="kpi-card">
                <div class="kpi-value">{{ "{:,}".format(total_sent) }}</div>
                <div class="kpi-label">Emails Enviados</div>
            </div>
            <div class="kpi-card">
                <div class="kpi-value">{{ "{:,}".format(total_delivered) }}</div>
                <div class="kpi-label">Entregados</div>
            </div>
            <div class="kpi-card">
                <div class="kpi-value">{{ "{:,}".format(total_bounced) }}</div>
                <div class="kpi-label">Bounced</div>
            </div>
            <div class="kpi-card">
                <div class="kpi-value">{{ "{:,}".format(total_complaints) }}</div>
                <div class="kpi-label">Quejas</div>
            </div>
        </div>
        <div class="kpi-grid">
            <div class="kpi-card">
                <div class="kpi-value {{ 'good' if overall_delivery_rate >= 95 else 'warn' if overall_delivery_rate >= 90 else 'bad' }}">{{ overall_delivery_rate }}%</div>
                <div class="kpi-label">Delivery Rate</div>
            </div>
            <div class="kpi-card">
                <div class="kpi-value {{ 'good' if overall_bounce_rate <= 2 else 'warn' if overall_bounce_rate <= 5 else 'bad' }}">{{ overall_bounce_rate }}%</div>
                <div class="kpi-label">Bounce Rate</div>
            </div>
            <div class="kpi-card">
                <div class="kpi-value {{ 'good' if overall_complaint_rate <= 0.08 else 'warn' if overall_complaint_rate <= 0.1 else 'bad' }}">{{ overall_complaint_rate }}%</div>
                <div class="kpi-label">Complaint Rate</div>
            </div>
            <div class="kpi-card">
                <div class="kpi-value">{{ overall_open_rate }}%</div>
                <div class="kpi-label">Open Rate</div>
            </div>
        </div>
    </div>

    {% if domains %}
    <div class="section">
        <div class="section-title">Reporte por Dominio</div>
        <table>
            <thead>
                <tr>
                    <th>Dominio</th>
                    <th>Enviados</th>
                    <th>Entregados</th>
                    <th>Bounced</th>
                    <th>Quejas</th>
                    <th>Delivery %</th>
                    <th>Bounce %</th>
                    <th>Reputacion</th>
                </tr>
            </thead>
            <tbody>
                {% for d in domains %}
                <tr>
                    <td><strong>{{ d.domain }}</strong></td>
                    <td>{{ "{:,}".format(d.total_sent) }}</td>
                    <td>{{ "{:,}".format(d.total_delivered) }}</td>
                    <td>{{ "{:,}".format(d.total_bounced) }}</td>
                    <td>{{ "{:,}".format(d.total_complaints) }}</td>
                    <td class="{{ 'good' if d.delivery_rate >= 95 else 'warn' if d.delivery_rate >= 90 else 'bad' }}">{{ d.delivery_rate }}%</td>
                    <td class="{{ 'good' if d.bounce_rate <= 2 else 'warn' if d.bounce_rate <= 5 else 'bad' }}">{{ d.bounce_rate }}%</td>
                    <td><span class="{{ 'good' if d.reputation_score >= 90 else 'warn' if d.reputation_score >= 70 else 'bad' }}">{{ d.reputation_label }} ({{ d.reputation_score }})</span></td>
                </tr>
                {% endfor %}
            </tbody>
        </table>
    </div>
    {% endif %}

    {% if trends %}
    <div class="section">
        <div class="section-title">Tendencia Diaria</div>
        <table>
            <thead>
                <tr>
                    <th>Fecha</th>
                    <th>Enviados</th>
                    <th>Entregados</th>
                    <th>Bounced</th>
                    <th>Quejas</th>
                    <th>Delivery %</th>
                    <th>Bounce %</th>
                </tr>
            </thead>
            <tbody>
                {% for t in trends[-14:] %}
                <tr>
                    <td>{{ t.date }}</td>
                    <td>{{ "{:,}".format(t.sent) }}</td>
                    <td>{{ "{:,}".format(t.delivered) }}</td>
                    <td>{{ "{:,}".format(t.bounced) }}</td>
                    <td>{{ "{:,}".format(t.complaints) }}</td>
                    <td class="{{ 'good' if t.delivery_rate >= 95 else 'warn' if t.delivery_rate >= 90 else 'bad' }}">{{ t.delivery_rate }}%</td>
                    <td class="{{ 'good' if t.bounce_rate <= 2 else 'warn' if t.bounce_rate <= 5 else 'bad' }}">{{ t.bounce_rate }}%</td>
                </tr>
                {% endfor %}
            </tbody>
        </table>
    </div>
    {% endif %}

    <div class="footer">
        MailPulse — Deliverability Dashboard | Generado automaticamente
    </div>
</body>
</html>
"""


def generate_report_pdf(report_data: dict) -> BytesIO:
    """Generate PDF from report data using WeasyPrint."""
    env = Environment(loader=BaseLoader())
    template = env.from_string(REPORT_TEMPLATE)

    html_content = template.render(**report_data)
    pdf_bytes = HTML(string=html_content).write_pdf()

    buffer = BytesIO(pdf_bytes)
    buffer.seek(0)
    return buffer
