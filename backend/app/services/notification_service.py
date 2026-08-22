import logging
import datetime
from typing import Dict, Any, Optional
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

# Notification Templates (EN / HI / MR)
NOTIFICATION_TEMPLATES: Dict[str, Dict[str, str]] = {
    "APPLICATION_CREATED": {
        "en": "✅ Your {cert_name} application has been started!\nTracking ID: {tracking_id}\nWe will guide you through each step.",
        "hi": "✅ आपका {cert_name} आवेदन शुरू हो गया!\nट्रैकिंग ID: {tracking_id}",
        "mr": "✅ तुमचा {cert_name} अर्ज सुरू झाला!\nट्रॅकिंग ID: {tracking_id}",
    },
    "DOCUMENT_VERIFIED": {
        "en": "📋 Documents verified successfully for {cert_name}!\nTracking ID: {tracking_id}",
        "hi": "📋 {cert_name} के लिए दस्तावेज़ सत्यापित हो गए!\nट्रैकिंग ID: {tracking_id}",
        "mr": "📋 {cert_name} साठी कागदपत्रे सत्यापित झाली!\nट्रॅकिंग ID: {tracking_id}",
    },
    "DOCUMENT_REJECTED": {
        "en": "⚠️ Document rejected: {doc_type}.\nReason: {reason}\nPlease re-upload a valid document.",
        "hi": "⚠️ दस्तावेज़ अस्वीकार: {doc_type}. कारण: {reason}",
        "mr": "⚠️ कागदपत्र नाकारले: {doc_type}. कारण: {reason}",
    },
    "PAYMENT_REQUIRED": {
        "en": "💳 Payment required for {cert_name}.\nAmount: ₹{amount}\nUPI ID: {upi_id}\nReference: {tracking_id}\n\nAfter payment, upload your receipt.",
        "hi": "💳 {cert_name} के लिए ₹{amount} का भुगतान करें।\nUPI: {upi_id}\nसंदर्भ: {tracking_id}",
        "mr": "💳 {cert_name} साठी ₹{amount} भरा.\nUPI: {upi_id}\nसंदर्भ: {tracking_id}",
    },
    "PAYMENT_VERIFIED": {
        "en": "✅ Payment of ₹{amount} received!\nTracking ID: {tracking_id}\nYour application will now be submitted.",
        "hi": "✅ ₹{amount} का भुगतान प्राप्त हुआ!\nट्रैकिंग ID: {tracking_id}",
        "mr": "✅ ₹{amount} भरणा प्राप्त झाला!\nट्रॅकिंग ID: {tracking_id}",
    },
    "APPLICATION_SUBMITTED": {
        "en": "🎉 Application submitted successfully!\n\nCertificate: {cert_name}\nTracking ID: {tracking_id}\nExpected: {days} working days\n\nTrack at any time using your Tracking ID.",
        "hi": "🎉 आवेदन सफलतापूर्वक जमा हो गया!\nट्रैकिंग ID: {tracking_id}\nअपेक्षित समय: {days} कार्य दिवस",
        "mr": "🎉 अर्ज यशस्वीरित्या सादर झाला!\nट्रॅकिंग ID: {tracking_id}\nअपेक्षित वेळ: {days} कामकाजाचे दिवस",
    },
    "CERTIFICATE_ISSUED": {
        "en": "🏛️ Your {cert_name} is ready!\nCertificate No: {cert_no}\nTracking ID: {tracking_id}\n\nDownload: {download_link}",
        "hi": "🏛️ आपका {cert_name} तैयार है!\nप्रमाण पत्र संख्या: {cert_no}\nट्रैकिंग ID: {tracking_id}",
        "mr": "🏛️ तुमचे {cert_name} तयार आहे!\nप्रमाणपत्र क्र.: {cert_no}\nट्रॅकिंग ID: {tracking_id}",
    },
    "DEPENDENCY_REQUIRED": {
        "en": "📋 {cert_name} requires {dep_cert} first.\n\nI've paused your {cert_name} application and will help you apply for {dep_cert} now. Your data is saved!",
        "hi": "{cert_name} के लिए पहले {dep_cert} आवश्यक है। आपका {cert_name} आवेदन रोक दिया गया है।",
        "mr": "{cert_name} साठी आधी {dep_cert} आवश्यक आहे. तुमचा अर्ज थांबवला आहे.",
    },
    "ELIGIBILITY_FAILED": {
        "en": "❌ Eligibility check failed for {cert_name}.\nReason: {reason}\n\nWould you like to apply for a different certificate?",
        "hi": "❌ {cert_name} के लिए पात्रता जांच विफल।\nकारण: {reason}",
        "mr": "❌ {cert_name} साठी पात्रता तपासणी अयशस्वी.\nकारण: {reason}",
    },
}


class NotificationService:
    """
    Sends multi-channel notifications (WhatsApp, SMS, Email) at application lifecycle events.
    For POC: Logs and stores notification records in DB.
    For production: Integrate WhatsApp Cloud API, Twilio, SendGrid.
    """

    @staticmethod
    def format_message(event: str, language: str, context: Dict[str, Any]) -> str:
        template = NOTIFICATION_TEMPLATES.get(event, {})
        msg_template = template.get(language) or template.get("en", "Application update: {tracking_id}")
        try:
            return msg_template.format(**context)
        except KeyError:
            return msg_template

    @staticmethod
    def notify(
        event: str,
        tracking_id: str,
        citizen_name: str,
        citizen_phone: str,
        language: str = "en",
        extra_data: Optional[Dict] = None,
        db: Optional[Session] = None,
        app_id: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        Dispatch notification for a lifecycle event.
        Logs to DB (NotificationLog model) and returns mock delivery result.
        """
        context = {
            "tracking_id": tracking_id,
            "citizen_name": citizen_name,
            "cert_name": (extra_data or {}).get("cert_name", "Certificate"),
            "dep_cert": (extra_data or {}).get("dep_cert", "prerequisite certificate"),
            "amount": (extra_data or {}).get("amount", "50"),
            "days": (extra_data or {}).get("days", "15"),
            "upi_id": "maharashtra.revenue@upi",
            "reason": (extra_data or {}).get("reason", ""),
            "doc_type": (extra_data or {}).get("doc_type", "Document"),
            "cert_no": (extra_data or {}).get("cert_no", "N/A"),
            "download_link": (extra_data or {}).get("download_link", "#"),
        }
        message = NotificationService.format_message(event, language, context)

        # Log notification (mock delivery for POC)
        result = {
            "event": event,
            "whatsapp": {"sent": True, "message_id": f"wa_{tracking_id}_{event}"},
            "sms": {"sent": True, "reference": f"sms_{tracking_id}"},
            "message": message,
        }

        # Persist to DB if available
        if db and app_id:
            try:
                from backend.app.models.models import AuditLog
                audit = AuditLog(
                    application_id=app_id,
                    event_type=f"NOTIFICATION_{event}",
                    event_data={
                        "channel": "whatsapp,sms",
                        "language": language,
                        "tracking_id": tracking_id,
                        "message": message[:500],
                    },
                )
                db.add(audit)
                db.commit()
            except Exception as e:
                logger.warning(f"Could not persist notification log: {e}")

        logger.info(f"[NOTIFY] {event} → {citizen_phone or 'N/A'} ({language}): {message[:100]}...")
        return result
