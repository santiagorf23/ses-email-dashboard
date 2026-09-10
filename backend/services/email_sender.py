"""
MailPulse — SES Dashboard
services/email_sender.py

Email sending service for reports.
"""
import logging
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders

logger = logging.getLogger(__name__)


def send_report_email(
    to_email: str,
    subject: str,
    html_body: str,
    pdf_bytes: bytes = None,
    pdf_filename: str = "report.pdf",
    smtp_config: dict = None,
) -> bool:
    """Send report email with optional PDF attachment."""
    if not smtp_config:
        smtp_config = {
            "host": "smtp.gmail.com",
            "port": 587,
            "user": None,
            "password": None,
            "from_email": None,
        }

    host = smtp_config.get("host", "smtp.gmail.com")
    port = smtp_config.get("port", 587)
    user = smtp_config.get("user")
    password = smtp_config.get("password")
    from_email = smtp_config.get("from_email") or user

    if not user or not password:
        logger.warning("SMTP credentials not configured, skipping email send")
        return False

    msg = MIMEMultipart()
    msg["From"] = from_email
    msg["To"] = to_email
    msg["Subject"] = subject

    msg.attach(MIMEText(html_body, "html"))

    if pdf_bytes:
        part = MIMEBase("application", "pdf")
        part.set_payload(pdf_bytes)
        encoders.encode_base64(part)
        part.add_header(
            "Content-Disposition",
            f"attachment; filename={pdf_filename}",
        )
        msg.attach(part)

    try:
        with smtplib.SMTP(host, port) as server:
            server.starttls()
            server.login(user, password)
            server.send_message(msg)
        logger.info("Report email sent to %s", to_email)
        return True
    except Exception as e:
        logger.error("Failed to send email: %s", e)
        return False
