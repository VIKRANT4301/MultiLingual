import os
import random
import string
import logging
import datetime
from typing import Dict, Any, Optional
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

MOCK_UPI_ID = "maharashtra.revenue@upi"


class PaymentService:
    """
    Handles payment initiation, receipt OCR verification and receipt PDF generation.
    For POC: Uses mock payment. For production: Integrate Razorpay / PayU.
    """

    @staticmethod
    def initiate_payment(app_id: int, service_id: str, db: Session) -> Dict[str, Any]:
        """
        Creates a payment record and returns payment instructions for the citizen.
        """
        from backend.app.models.models import Payment, Application
        from backend.app.services.service_loader import ServiceLoader
        from backend.app.services.tracking_service import TrackingService

        app = db.query(Application).filter(Application.id == app_id).first()
        if not app:
            return {"error": "Application not found"}

        fee = ServiceLoader.get_fee(service_id)
        cert_name = ServiceLoader.load_service(service_id).get("name", {}).get("en", service_id)

        # Get or create tracking_id
        app_state = app.states
        tracking_id = (app_state.state_data or {}).get("tracking_id")
        if not tracking_id:
            tracking_id = TrackingService.generate_tracking_id(service_id)
            TrackingService.save_tracking_id(app_state, tracking_id, db)

        # Create Payment record
        payment_ref = "".join(random.choices(string.ascii_uppercase + string.digits, k=12))
        payment = Payment(
            application_id=app_id,
            amount=fee,
            payment_method="UPI",
            status="INITIATED",
            transaction_no=f"PAY-{payment_ref}",
        )
        db.add(payment)
        db.commit()
        db.refresh(payment)

        return {
            "payment_id": payment.id,
            "transaction_ref": payment.transaction_no,
            "amount": fee,
            "currency": "INR",
            "certificate_name": cert_name,
            "tracking_id": tracking_id,
            "upi_id": MOCK_UPI_ID,
            "instructions": {
                "en": f"Please pay ₹{fee:.0f} to UPI ID {MOCK_UPI_ID} with reference {tracking_id}. After payment, upload your receipt.",
                "hi": f"UPI ID {MOCK_UPI_ID} पर ₹{fee:.0f} का भुगतान करें। संदर्भ: {tracking_id}",
                "mr": f"UPI ID {MOCK_UPI_ID} वर ₹{fee:.0f} भरा. संदर्भ: {tracking_id}",
            }
        }

    @staticmethod
    def verify_payment_receipt(
        receipt_path: str,
        expected_amount: float,
        app_id: int,
        db: Session
    ) -> Dict[str, Any]:
        """
        OCR the uploaded payment receipt and verify amount, transaction ID, and authenticity.
        For POC: Uses structured mock extraction.
        For production: Replace with real OCR (pytesseract / Cloud Vision).
        """
        from backend.app.models.models import Payment

        # Mock OCR extraction from receipt
        file_lower = receipt_path.lower() if receipt_path else ""
        is_mismatch = "wrong" in file_lower or "invalid" in file_lower or "fake" in file_lower

        confidence = round(random.uniform(0.92, 0.99), 2)

        extracted = {
            "amount": expected_amount * 2 if is_mismatch else expected_amount,
            "transaction_id": "" if is_mismatch else f"UPI{datetime.datetime.now().strftime('%Y%m%d%H%M%S')}",
            "payment_date": datetime.datetime.now().strftime("%d-%m-%Y"),
            "payment_time": datetime.datetime.now().strftime("%H:%M:%S"),
            "payer_name": "Krunal Wandhare",
            "payment_gateway": "BHIM UPI",
        }

        issues = []
        action = "ACCEPT"

        # Validate amount (allow ±5% tolerance)
        if abs(extracted["amount"] - expected_amount) > expected_amount * 0.05:
            issues.append(f"Amount mismatch: expected ₹{expected_amount:.0f}, found ₹{extracted['amount']:.0f}")
            action = "REJECT"

        # Validate transaction ID
        if not extracted.get("transaction_id"):
            issues.append("Transaction ID missing from receipt")
            action = "ESCALATE"

        # Check for duplicate transaction
        if extracted.get("transaction_id") and db:
            existing = db.query(Payment).filter(
                Payment.transaction_no == extracted["transaction_id"]
            ).first()
            if existing:
                issues.append("Duplicate transaction ID detected")
                action = "REJECT"

        # Update payment record status
        if action == "ACCEPT" and db:
            payment = db.query(Payment).filter(
                Payment.application_id == app_id,
                Payment.status == "INITIATED"
            ).order_by(Payment.created_at.desc()).first()
            if payment:
                payment.status = "SUCCESS"
                payment.transaction_no = extracted.get("transaction_id", payment.transaction_no)
                db.commit()

        return {
            "verified": action == "ACCEPT",
            "confidence": confidence,
            "extracted": extracted,
            "issues": issues,
            "action": action,
        }
