import logging

logger = logging.getLogger(__name__)


def send_prospect_confirmation(to_email: str, first_name: str) -> bool:
    try:
        from app.config import get_settings
        import resend
        settings = get_settings()
        resend.api_key = settings.RESEND_API_KEY
        resend.Emails.send({
            "from": settings.RESEND_FROM_EMAIL,
            "to": to_email,
            "subject": "We received your application",
            "html": f"<p>Hi {first_name}, we received your application.</p>",
        })
        return True
    except Exception as exc:
        logger.warning("send_prospect_confirmation failed: %s", exc)
        return False


def send_attorney_notification(attorney_email: str, lead) -> bool:
    try:
        from app.config import get_settings
        import resend
        settings = get_settings()
        resend.api_key = settings.RESEND_API_KEY
        resend.Emails.send({
            "from": settings.RESEND_FROM_EMAIL,
            "to": attorney_email,
            "subject": f"New lead: {lead.first_name} {lead.last_name}",
            "html": f"<p>New lead received from {lead.email}.</p>",
        })
        return True
    except Exception as exc:
        logger.warning("send_attorney_notification failed: %s", exc)
        return False
