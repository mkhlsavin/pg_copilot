"""
SMTP Email notification service.

Sends lead notifications via email.
"""

import logging
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Any, Dict

import aiosmtplib

from src.config import get_settings

logger = logging.getLogger(__name__)


class EmailNotifier:
    """SMTP email notification service."""

    def __init__(
        self,
        smtp_host: str | None = None,
        smtp_port: int | None = None,
        smtp_user: str | None = None,
        smtp_password: str | None = None,
        from_email: str | None = None,
        admin_email: str | None = None,
    ):
        """
        Initialize Email notifier.

        Args:
            smtp_host: SMTP server hostname
            smtp_port: SMTP server port
            smtp_user: SMTP username
            smtp_password: SMTP password
            from_email: Sender email address
            admin_email: Admin email to receive notifications
        """
        settings = get_settings()
        self.smtp_host = smtp_host or settings.smtp_host
        self.smtp_port = smtp_port or settings.smtp_port
        self.smtp_user = smtp_user or settings.smtp_user
        self.smtp_password = smtp_password or settings.smtp_password
        self.from_email = from_email or settings.smtp_from_email
        self.admin_email = admin_email or settings.admin_email
        self.use_tls = settings.smtp_use_tls
        self._enabled = bool(self.smtp_user and self.smtp_password and self.admin_email)

    @property
    def enabled(self) -> bool:
        """Check if email notifications are enabled."""
        return self._enabled

    async def send_new_lead_notification(self, lead_data: Dict[str, Any]) -> bool:
        """
        Send email notification for new lead.

        Args:
            lead_data: Lead data dictionary

        Returns:
            True if sent successfully, False otherwise
        """
        if not self.enabled:
            logger.debug("Email notifications disabled, skipping")
            return False

        subject = f"[CodeGraph] Новая заявка: {lead_data['company']}"
        body_text = self._format_lead_email_text(lead_data)
        body_html = self._format_lead_email_html(lead_data)

        return await self._send_email(self.admin_email, subject, body_text, body_html)

    def _format_lead_email_text(self, lead: Dict[str, Any]) -> str:
        """Format lead data into plain text email."""
        team_size = lead.get("team_size") or "Не указан"
        language = lead.get("language") or "Не указан"
        position = lead.get("position") or "Не указана"

        # Language display names
        language_names = {
            "c-cpp": "C/C++",
            "java": "Java",
            "python": "Python",
            "go": "Go",
            "javascript": "JavaScript/TypeScript",
            "csharp": "C#",
            "other": "Другой",
        }
        language_display = language_names.get(language, language)

        # Format created_at
        created_at = lead.get("created_at", "N/A")
        if hasattr(created_at, "strftime"):
            created_at = created_at.strftime("%Y-%m-%d %H:%M:%S")

        return f"""
Новая заявка на демо CodeGraph

Контактная информация:
  Имя: {lead['name']}
  Email: {lead['email']}
  Компания: {lead['company']}
  Должность: {position}

Информация о проекте:
  Размер команды: {team_size}
  Основной язык: {language_display}

Техническая информация:
  Дата отправки: {created_at}
  IP адрес: {lead.get('ip_address') or 'N/A'}
  Источник: {lead.get('source', 'landing')}

---
CodeGraph Lead Management System
https://codegraph.ru
        """.strip()

    def _format_lead_email_html(self, lead: Dict[str, Any]) -> str:
        """Format lead data into HTML email."""
        team_size = lead.get("team_size") or "Не указан"
        language = lead.get("language") or "Не указан"
        position = lead.get("position") or "Не указана"

        language_names = {
            "c-cpp": "C/C++",
            "java": "Java",
            "python": "Python",
            "go": "Go",
            "javascript": "JavaScript/TypeScript",
            "csharp": "C#",
            "other": "Другой",
        }
        language_display = language_names.get(language, language)

        created_at = lead.get("created_at", "N/A")
        if hasattr(created_at, "strftime"):
            created_at = created_at.strftime("%Y-%m-%d %H:%M:%S")

        return f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <style>
        body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; line-height: 1.6; color: #333; }}
        .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
        .header {{ background: linear-gradient(135deg, #3B82F6, #6366F1); color: white; padding: 20px; border-radius: 8px 8px 0 0; }}
        .header h1 {{ margin: 0; font-size: 24px; }}
        .content {{ background: #f9fafb; padding: 20px; border: 1px solid #e5e7eb; border-top: none; }}
        .section {{ background: white; padding: 15px; margin-bottom: 15px; border-radius: 6px; border: 1px solid #e5e7eb; }}
        .section h3 {{ margin-top: 0; color: #374151; font-size: 14px; text-transform: uppercase; letter-spacing: 0.5px; }}
        .field {{ display: flex; padding: 8px 0; border-bottom: 1px solid #f3f4f6; }}
        .field:last-child {{ border-bottom: none; }}
        .field-label {{ font-weight: 600; color: #6b7280; width: 140px; flex-shrink: 0; }}
        .field-value {{ color: #111827; }}
        .footer {{ text-align: center; padding: 20px; color: #6b7280; font-size: 12px; }}
        .email-link {{ color: #3B82F6; text-decoration: none; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🎯 Новая заявка на демо</h1>
        </div>
        <div class="content">
            <div class="section">
                <h3>👤 Контактная информация</h3>
                <div class="field">
                    <span class="field-label">Имя:</span>
                    <span class="field-value">{lead['name']}</span>
                </div>
                <div class="field">
                    <span class="field-label">Email:</span>
                    <span class="field-value"><a href="mailto:{lead['email']}" class="email-link">{lead['email']}</a></span>
                </div>
                <div class="field">
                    <span class="field-label">Компания:</span>
                    <span class="field-value">{lead['company']}</span>
                </div>
                <div class="field">
                    <span class="field-label">Должность:</span>
                    <span class="field-value">{position}</span>
                </div>
            </div>
            <div class="section">
                <h3>💻 Информация о проекте</h3>
                <div class="field">
                    <span class="field-label">Размер команды:</span>
                    <span class="field-value">{team_size}</span>
                </div>
                <div class="field">
                    <span class="field-label">Основной язык:</span>
                    <span class="field-value">{language_display}</span>
                </div>
            </div>
            <div class="section">
                <h3>📊 Техническая информация</h3>
                <div class="field">
                    <span class="field-label">Дата отправки:</span>
                    <span class="field-value">{created_at}</span>
                </div>
                <div class="field">
                    <span class="field-label">IP адрес:</span>
                    <span class="field-value">{lead.get('ip_address') or 'N/A'}</span>
                </div>
                <div class="field">
                    <span class="field-label">Источник:</span>
                    <span class="field-value">{lead.get('source', 'landing')}</span>
                </div>
            </div>
        </div>
        <div class="footer">
            <p>CodeGraph Lead Management System<br>
            <a href="https://codegraph.ru" class="email-link">codegraph.ru</a></p>
        </div>
    </div>
</body>
</html>
        """.strip()

    async def _send_email(
        self,
        to: str,
        subject: str,
        body_text: str,
        body_html: str | None = None,
    ) -> bool:
        """
        Send email via SMTP.

        Args:
            to: Recipient email address
            subject: Email subject
            body_text: Plain text body
            body_html: Optional HTML body

        Returns:
            True if sent successfully, False otherwise
        """
        try:
            msg = MIMEMultipart("alternative")
            msg["From"] = self.from_email
            msg["To"] = to
            msg["Subject"] = subject

            # Attach plain text version
            msg.attach(MIMEText(body_text, "plain", "utf-8"))

            # Attach HTML version if provided
            if body_html:
                msg.attach(MIMEText(body_html, "html", "utf-8"))

            # Send email
            await aiosmtplib.send(
                msg,
                hostname=self.smtp_host,
                port=self.smtp_port,
                username=self.smtp_user,
                password=self.smtp_password,
                start_tls=self.use_tls,
            )

            logger.info(f"Email sent to {to}: {subject}")
            return True

        except aiosmtplib.SMTPException as e:
            logger.error(f"SMTP error sending email: {e}")
            return False
        except Exception as e:
            logger.exception(f"Failed to send email: {e}")
            return False

    async def test_connection(self) -> bool:
        """
        Test SMTP connection.

        Returns:
            True if connection works, False otherwise
        """
        if not self.enabled:
            return False

        try:
            smtp = aiosmtplib.SMTP(
                hostname=self.smtp_host,
                port=self.smtp_port,
            )
            await smtp.connect()
            if self.use_tls:
                await smtp.starttls()
            await smtp.login(self.smtp_user, self.smtp_password)
            await smtp.quit()
            logger.info(f"SMTP connection test successful: {self.smtp_host}:{self.smtp_port}")
            return True
        except Exception as e:
            logger.error(f"SMTP connection test failed: {e}")
            return False
