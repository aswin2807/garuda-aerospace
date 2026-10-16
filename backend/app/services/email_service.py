import json
import logging
import smtplib
from datetime import datetime, timezone
from email.message import EmailMessage
from pathlib import Path
from typing import Any, Dict, List, Optional

from backend.app.core.config import settings

logger = logging.getLogger(__name__)


class EmailDeliveryResult:
    def __init__(
        self,
        sent: bool,
        provider: str,
        recipient: str,
        subject: str,
        error: Optional[str] = None,
    ):
        self.sent = sent
        self.provider = provider
        self.recipient = recipient
        self.subject = subject
        self.error = error


class EmailService:
    """
    Transactional email delivery service for Garuda Aerospace authentication workflows.
    Supports SMTP / SMTP_SSL delivery configured via environment variables and falls back
    gracefully when SMTP is unconfigured in local/test environments while recording
    delivery status without ever logging sensitive tokens or passwords.
    """

    def __init__(self) -> None:
        # In-memory outbox for automated testing & local inspection (never logged to stdout)
        self.outbox: List[Dict[str, Any]] = []

    def _build_mime_message(
        self,
        to_email: str,
        subject: str,
        plain_body: str,
        html_body: str,
    ) -> EmailMessage:
        msg = EmailMessage()
        from_header = (
            f"{settings.SMTP_FROM_NAME} <{settings.SMTP_FROM_EMAIL}>"
            if settings.SMTP_FROM_NAME
            else settings.SMTP_FROM_EMAIL
        )
        msg["Subject"] = subject
        msg["From"] = from_header
        msg["To"] = to_email
        msg.set_content(plain_body)
        msg.add_alternative(html_body, subtype="html")
        return msg

    def _send_via_smtp(self, msg: EmailMessage, to_email: str) -> EmailDeliveryResult:
        host = (settings.SMTP_HOST or "").strip()
        if not host:
            return EmailDeliveryResult(
                sent=False,
                provider="unconfigured",
                recipient=to_email,
                subject=str(msg["Subject"]),
                error="SMTP_HOST is not configured",
            )

        try:
            if settings.SMTP_USE_SSL:
                with smtplib.SMTP_SSL(host, settings.SMTP_PORT, timeout=10) as server:
                    if settings.SMTP_USERNAME and settings.SMTP_PASSWORD:
                        server.login(settings.SMTP_USERNAME, settings.SMTP_PASSWORD)
                    server.send_message(msg)
            else:
                with smtplib.SMTP(host, settings.SMTP_PORT, timeout=10) as server:
                    server.ehlo()
                    if settings.SMTP_USE_TLS:
                        server.starttls()
                        server.ehlo()
                    if settings.SMTP_USERNAME and settings.SMTP_PASSWORD:
                        server.login(settings.SMTP_USERNAME, settings.SMTP_PASSWORD)
                    server.send_message(msg)

            logger.info(
                "Email delivered via SMTP: recipient=%s subject='%s' status=SENT",
                to_email,
                msg["Subject"],
            )
            return EmailDeliveryResult(
                sent=True,
                provider="smtp",
                recipient=to_email,
                subject=str(msg["Subject"]),
            )
        except Exception as exc:
            logger.error(
                "SMTP email delivery failed: recipient=%s subject='%s' error=%s",
                to_email,
                msg["Subject"],
                exc.__class__.__name__,
            )
            return EmailDeliveryResult(
                sent=False,
                provider="smtp",
                recipient=to_email,
                subject=str(msg["Subject"]),
                error=str(exc),
            )

    def _record_outbox(
        self,
        email_type: str,
        to_email: str,
        subject: str,
        plain_body: str,
        html_body: str,
        action_url: Optional[str],
        delivery_result: EmailDeliveryResult,
    ) -> None:
        entry = {
            "email_type": email_type,
            "recipient": to_email,
            "subject": subject,
            "plain_body": plain_body,
            "html_body": html_body,
            "action_url": action_url,
            "sent_via_smtp": delivery_result.sent,
            "provider": delivery_result.provider,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        self.outbox.append(entry)
        # Keep outbox bounded in memory
        if len(self.outbox) > 200:
            self.outbox = self.outbox[-200:]

        # Persist to local outbox directory if configured and not in production
        if settings.ENVIRONMENT.lower() in ("development", "test", "local"):
            try:
                out_dir = Path(settings.EMAIL_DEV_OUTBOX_DIR)
                out_dir.mkdir(parents=True, exist_ok=True)
                latest_file = out_dir / "latest_emails.json"
                existing: List[Dict[str, Any]] = []
                if latest_file.exists():
                    try:
                        existing = json.loads(latest_file.read_text(encoding="utf-8"))
                    except Exception:
                        existing = []
                existing.append(entry)
                latest_file.write_text(
                    json.dumps(existing[-50:], indent=2),
                    encoding="utf-8",
                )
            except Exception:
                pass

    def send_verification_email(
        self,
        to_email: str,
        full_name: str,
        raw_token: str,
    ) -> EmailDeliveryResult:
        verify_url = f"{settings.FRONTEND_URL.rstrip('/')}/verify-email?token={raw_token}"
        expire_hours = settings.EMAIL_VERIFY_EXPIRE_HOURS
        subject = "Verify Your Garuda Aerospace Account"
        greeting_name = full_name.strip() if full_name else "Operator"

        plain_body = (
            f"Hello {greeting_name},\n\n"
            f"Welcome to Garuda Aerospace. Please verify your email address to activate your account.\n\n"
            f"Verify your account using the link below:\n"
            f"{verify_url}\n\n"
            f"This verification link will expire in {expire_hours} hours and can only be used once.\n\n"
            f"If you did not create a Garuda Aerospace account, you can safely ignore this email.\n\n"
            f"— Garuda Aerospace Security"
        )

        html_body = f"""<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8" />
  <title>{subject}</title>
</head>
<body style="margin:0;padding:0;background-color:#07111f;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,Helvetica,Arial,sans-serif;color:#f8fafc;">
  <table width="100%" cellpadding="0" cellspacing="0" style="background-color:#07111f;padding:36px 16px;">
    <tr>
      <td align="center">
        <table width="560" cellpadding="0" cellspacing="0" style="background-color:#0e1b2e;border:1px solid #1e324d;border-radius:12px;padding:36px 32px;">
          <tr>
            <td style="padding-bottom:20px;border-bottom:1px solid #1e324d;">
              <span style="font-size:18px;font-weight:700;letter-spacing:1.2px;color:#ffffff;text-transform:uppercase;">GARUDA AEROSPACE</span>
            </td>
          </tr>
          <tr>
            <td style="padding-top:24px;font-size:15px;line-height:1.6;color:#cbd5e1;">
              <p style="margin:0 0 16px 0;color:#ffffff;font-weight:600;">Hello {greeting_name},</p>
              <p style="margin:0 0 20px 0;">Thank you for registering with <strong>Garuda Aerospace</strong>. Please confirm your email address to activate your account and access the surveillance and navigation modules.</p>
              <p style="margin:28px 0;" align="center">
                <a href="{verify_url}" style="background-color:#2563eb;color:#ffffff;text-decoration:none;padding:13px 28px;border-radius:8px;font-weight:600;font-size:14px;display:inline-block;">Verify Email Address</a>
              </p>
              <p style="margin:0 0 14px 0;font-size:13px;color:#94a3b8;">This verification link will expire in <strong>{expire_hours} hours</strong> and can only be used once.</p>
              <p style="margin:0;font-size:13px;color:#64748b;">If you did not request a Garuda Aerospace account, you can safely ignore this email.</p>
            </td>
          </tr>
        </table>
      </td>
    </tr>
  </table>
</body>
</html>"""

        msg = self._build_mime_message(to_email, subject, plain_body, html_body)
        result = self._send_via_smtp(msg, to_email)
        if not result.sent and result.provider == "unconfigured":
            logger.info(
                "Verification email queued in local outbox (SMTP unconfigured): recipient=%s status=QUEUED",
                to_email,
            )
            result.sent = True
            result.provider = "local_outbox"

        self._record_outbox(
            email_type="EMAIL_VERIFICATION",
            to_email=to_email,
            subject=subject,
            plain_body=plain_body,
            html_body=html_body,
            action_url=verify_url,
            delivery_result=result,
        )
        return result

    def send_password_reset_email(
        self,
        to_email: str,
        full_name: str,
        raw_token: str,
    ) -> EmailDeliveryResult:
        reset_url = f"{settings.FRONTEND_URL.rstrip('/')}/reset-password?token={raw_token}"
        expire_minutes = settings.PASSWORD_RESET_EXPIRE_MINUTES
        subject = "Reset Your Garuda Aerospace Password"
        greeting_name = full_name.strip() if full_name else "Operator"

        plain_body = (
            f"Hello {greeting_name},\n\n"
            f"We received a request to reset the password for your Garuda Aerospace account.\n\n"
            f"Reset your password using the secure link below:\n"
            f"{reset_url}\n\n"
            f"This password reset link will expire in {expire_minutes} minutes and is valid for a single use.\n\n"
            f"If you did not request a password reset, you can safely ignore this email. Your password will remain unchanged.\n\n"
            f"— Garuda Aerospace Security"
        )

        html_body = f"""<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8" />
  <title>{subject}</title>
</head>
<body style="margin:0;padding:0;background-color:#07111f;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,Helvetica,Arial,sans-serif;color:#f8fafc;">
  <table width="100%" cellpadding="0" cellspacing="0" style="background-color:#07111f;padding:36px 16px;">
    <tr>
      <td align="center">
        <table width="560" cellpadding="0" cellspacing="0" style="background-color:#0e1b2e;border:1px solid #1e324d;border-radius:12px;padding:36px 32px;">
          <tr>
            <td style="padding-bottom:20px;border-bottom:1px solid #1e324d;">
              <span style="font-size:18px;font-weight:700;letter-spacing:1.2px;color:#ffffff;text-transform:uppercase;">GARUDA AEROSPACE</span>
            </td>
          </tr>
          <tr>
            <td style="padding-top:24px;font-size:15px;line-height:1.6;color:#cbd5e1;">
              <p style="margin:0 0 16px 0;color:#ffffff;font-weight:600;">Hello {greeting_name},</p>
              <p style="margin:0 0 20px 0;">We received a request to reset the password for your <strong>Garuda Aerospace</strong> account. Click the button below to choose a new password:</p>
              <p style="margin:28px 0;" align="center">
                <a href="{reset_url}" style="background-color:#2563eb;color:#ffffff;text-decoration:none;padding:13px 28px;border-radius:8px;font-weight:600;font-size:14px;display:inline-block;">Reset Password</a>
              </p>
              <p style="margin:0 0 14px 0;font-size:13px;color:#94a3b8;">This password reset link will expire in <strong>{expire_minutes} minutes</strong> and can only be used once.</p>
              <p style="margin:0;font-size:13px;color:#64748b;">If you did not request a password reset, you can safely ignore this email and your password will remain unchanged.</p>
            </td>
          </tr>
        </table>
      </td>
    </tr>
  </table>
</body>
</html>"""

        msg = self._build_mime_message(to_email, subject, plain_body, html_body)
        result = self._send_via_smtp(msg, to_email)
        if not result.sent and result.provider == "unconfigured":
            logger.info(
                "Password reset email queued in local outbox (SMTP unconfigured): recipient=%s status=QUEUED",
                to_email,
            )
            result.sent = True
            result.provider = "local_outbox"

        self._record_outbox(
            email_type="PASSWORD_RESET",
            to_email=to_email,
            subject=subject,
            plain_body=plain_body,
            html_body=html_body,
            action_url=reset_url,
            delivery_result=result,
        )
        return result

    def send_password_changed_email(
        self,
        to_email: str,
        full_name: str,
    ) -> EmailDeliveryResult:
        subject = "Your Garuda Aerospace Password Was Updated"
        greeting_name = full_name.strip() if full_name else "Operator"
        login_url = f"{settings.FRONTEND_URL.rstrip('/')}/login"

        plain_body = (
            f"Hello {greeting_name},\n\n"
            f"This is a confirmation that the password for your Garuda Aerospace account ({to_email}) has been successfully updated.\n\n"
            f"If you made this change, you can sign in with your new password at:\n"
            f"{login_url}\n\n"
            f"If you did not authorize this change, please contact your Garuda Aerospace administrator immediately.\n\n"
            f"— Garuda Aerospace Security"
        )

        html_body = f"""<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8" />
  <title>{subject}</title>
</head>
<body style="margin:0;padding:0;background-color:#07111f;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,Helvetica,Arial,sans-serif;color:#f8fafc;">
  <table width="100%" cellpadding="0" cellspacing="0" style="background-color:#07111f;padding:36px 16px;">
    <tr>
      <td align="center">
        <table width="560" cellpadding="0" cellspacing="0" style="background-color:#0e1b2e;border:1px solid #1e324d;border-radius:12px;padding:36px 32px;">
          <tr>
            <td style="padding-bottom:20px;border-bottom:1px solid #1e324d;">
              <span style="font-size:18px;font-weight:700;letter-spacing:1.2px;color:#ffffff;text-transform:uppercase;">GARUDA AEROSPACE</span>
            </td>
          </tr>
          <tr>
            <td style="padding-top:24px;font-size:15px;line-height:1.6;color:#cbd5e1;">
              <p style="margin:0 0 16px 0;color:#ffffff;font-weight:600;">Hello {greeting_name},</p>
              <p style="margin:0 0 20px 0;">The password for your <strong>Garuda Aerospace</strong> account (<code>{to_email}</code>) was recently changed. All previous active sessions have been signed out for your security.</p>
              <p style="margin:0;font-size:13px;color:#64748b;">If you did not perform this password change, please contact your system administrator immediately.</p>
            </td>
          </tr>
        </table>
      </td>
    </tr>
  </table>
</body>
</html>"""

        msg = self._build_mime_message(to_email, subject, plain_body, html_body)
        result = self._send_via_smtp(msg, to_email)
        if not result.sent and result.provider == "unconfigured":
            logger.info(
                "Password changed notification queued in local outbox (SMTP unconfigured): recipient=%s status=QUEUED",
                to_email,
            )
            result.sent = True
            result.provider = "local_outbox"

        self._record_outbox(
            email_type="PASSWORD_CHANGED",
            to_email=to_email,
            subject=subject,
            plain_body=plain_body,
            html_body=html_body,
            action_url=login_url,
            delivery_result=result,
        )
        return result


email_service = EmailService()
