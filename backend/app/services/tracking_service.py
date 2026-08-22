import secrets
import string
import datetime
import logging
from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

CERT_CODE_MAP = {
    "income_certificate": "INC",
    "caste_certificate": "CASTE",
    "domicile_certificate": "DOM",
    "ncl_certificate": "NCL",
    "solvency_certificate": "SOL",
    "nativity_certificate": "NAT",
    "obc_ncl_certificate": "NCL",
}


class TrackingService:
    """Generates and manages unique tracking IDs for citizen certificate applications."""

    @staticmethod
    def generate_tracking_id(service_id: str) -> str:
        """
        Generate unique tracking ID.
        Format: MH-{YEAR}-{CERT_CODE}-{8 UPPERCASE ALPHANUMERIC}
        Example: MH-2026-NCL-A83K92P1
        """
        year = datetime.datetime.now().year
        cert_code = CERT_CODE_MAP.get(service_id, "CERT")
        random_suffix = "".join(
            secrets.choice(string.ascii_uppercase + string.digits) for _ in range(8)
        )
        return f"MH-{year}-{cert_code}-{random_suffix}"

    @staticmethod
    def get_tracking_status(tracking_id: str, db: Session) -> Optional[Dict[str, Any]]:
        """
        Returns comprehensive application status for a tracking ID.
        """
        from backend.app.models.models import Application, ApplicationState, Document, Payment

        # Find application by tracking_id in state_data
        try:
            from sqlalchemy import func
            app_state = db.query(ApplicationState).filter(
                func.json_extract(ApplicationState.state_data, "$.tracking_id") == tracking_id
            ).first()

            if not app_state:
                return None

            app = db.query(Application).filter(Application.id == app_state.application_id).first()
            if not app:
                return None

            state_data = app_state.state_data or {}
            docs = db.query(Document).filter(Document.application_id == app.id).all()
            payments = db.query(Payment).filter(Payment.application_id == app.id).all()

            doc_verified = sum(1 for d in docs if d.status == "VALIDATED")
            doc_total = len(docs)
            payment_paid = any(p.status == "SUCCESS" for p in payments)
            payment_amount = next((p.amount for p in payments if p.status == "SUCCESS"), 0.0)

            from backend.app.services.service_loader import ServiceLoader
            processing_days = ServiceLoader.get_processing_days(app.service_id)
            cert_name = ServiceLoader.load_service(app.service_id).get("name", {}).get("en", app.service_id)

            expected_by = None
            if app.updated_at:
                expected_by = (app.updated_at + datetime.timedelta(days=processing_days)).strftime("%Y-%m-%d")

            next_step = TrackingService._get_next_step(app_state.current_state, payment_paid, doc_verified < doc_total)

            return {
                "tracking_id": tracking_id,
                "application_no": app.application_no,
                "certificate": cert_name,
                "status": app.status,
                "current_state": app_state.current_state,
                "submitted_on": app.created_at.strftime("%Y-%m-%d") if app.created_at else None,
                "expected_completion_by": expected_by,
                "payment": {
                    "status": "PAID" if payment_paid else "PENDING",
                    "amount": payment_amount,
                },
                "documents": {
                    "verified": doc_verified,
                    "total": doc_total,
                    "status": "VERIFIED" if (doc_total > 0 and doc_verified == doc_total) else "PENDING",
                },
                "next_step": next_step,
                "language": state_data.get("language", "en"),
            }
        except Exception as e:
            logger.error(f"Error fetching tracking status for {tracking_id}: {e}")
            return None

    @staticmethod
    def _get_next_step(current_state: str, payment_paid: bool, docs_pending: bool) -> str:
        step_messages = {
            "START": "Please start your application by selecting a certificate service.",
            "LANGUAGE_SELECTION": "Please select your preferred language.",
            "SERVICE_SELECTION": "Please select the certificate you want to apply for.",
            "INFORMATION_COLLECTION": "Please provide your personal details.",
            "CONSENT": "Please provide your consent to proceed.",
            "DOCUMENT_COLLECTION": "Please upload required documents.",
            "DOCUMENT_VALIDATION": "Documents are being verified.",
            "PREREQUISITE_REDIRECT": "Completing prerequisite certificate application.",
            "AUTHENTICATION": "Please complete Aadhaar authentication.",
            "FEE_CALCULATION": "Fee is being calculated.",
            "PAYMENT": "Please complete payment of ₹50 via UPI.",
            "RECEIPT": "Please upload your payment receipt.",
            "SUBMISSION": "Application is being submitted.",
            "STATUS_TRACKING": "Waiting for department review.",
            "CERTIFICATE_GENERATION": "Certificate is being generated.",
            "COMPLETED": "Application completed. Download your certificate.",
        }
        return step_messages.get(current_state, "Processing your application. Please wait.")

    @staticmethod
    def save_tracking_id(app_state, tracking_id: str, db: Session) -> None:
        """Saves tracking_id into state_data and commits."""
        from sqlalchemy.orm.attributes import flag_modified
        state_data = dict(app_state.state_data or {})
        state_data["tracking_id"] = tracking_id
        app_state.state_data = state_data
        if hasattr(app_state, "_sa_instance_state"):
            flag_modified(app_state, "state_data")
        db.commit()
