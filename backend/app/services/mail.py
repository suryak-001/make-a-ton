import logging
import smtplib
from email.message import EmailMessage

from app.config import settings

log = logging.getLogger("uvicorn.error")


# (file name, bytes, MIME type such as "application/pdf")
Attachment = tuple[str, bytes, str]


def send_mail(to: str, subject: str, body: str, attachments: list[Attachment] | None = None) -> None:
    """Sends via SMTP when SMTP_HOST is set; otherwise prints to the server console (dev)."""
    attachments = attachments or []
    if not settings.smtp_host:
        files = "".join(f"\n📎 {name} ({len(data) / 1024:.1f} KB)" for name, data, _ in attachments)
        log.warning("\n📧 [mail] to=%s subject=%r\n%s%s\n", to, subject, body, files)
        return
    msg = EmailMessage()
    msg["From"], msg["To"], msg["Subject"] = settings.mail_from, to, subject
    msg.set_content(body)
    for name, data, mime in attachments:
        main, sub = mime.split("/", 1)
        msg.add_attachment(data, maintype=main, subtype=sub, filename=name)
    with smtplib.SMTP(settings.smtp_host, settings.smtp_port) as smtp:
        smtp.starttls()
        if settings.smtp_user:
            smtp.login(settings.smtp_user, settings.smtp_pass)
        smtp.send_message(msg)
