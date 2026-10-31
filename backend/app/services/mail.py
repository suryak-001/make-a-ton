import logging
import smtplib
from email.message import EmailMessage

from app.config import settings

log = logging.getLogger("uvicorn.error")


def send_mail(to: str, subject: str, body: str) -> None:
    """Sends via SMTP when SMTP_HOST is set; otherwise prints to the server console (dev)."""
    if not settings.smtp_host:
        log.warning("\n📧 [mail] to=%s subject=%r\n%s\n", to, subject, body)
        return
    msg = EmailMessage()
    msg["From"], msg["To"], msg["Subject"] = settings.mail_from, to, subject
    msg.set_content(body)
    with smtplib.SMTP(settings.smtp_host, settings.smtp_port) as smtp:
        smtp.starttls()
        if settings.smtp_user:
            smtp.login(settings.smtp_user, settings.smtp_pass)
        smtp.send_message(msg)
