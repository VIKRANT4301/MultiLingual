import datetime
import logging
import random
from typing import Dict, Any, List, Tuple
from sqlalchemy.orm import Session
from backend.app.models.models import (
    Application, ApplicationState, Document, Payment, 
    AuditLog, Service, Escalation, Certificate
)

logger = logging.getLogger(__name__)

# Valid States
STATES = [
    "START",
    "LANGUAGE_SELECTION",
    "SERVICE_SELECTION",
    "INFORMATION_COLLECTION",
    "CONSENT",
    "FORM_VALIDATION",
    "DOCUMENT_COLLECTION",
    "DOCUMENT_VALIDATION",
    "AUTHENTICATION",
    "FEE_CALCULATION",
    "PAYMENT",
    "SUBMISSION",
    "RECEIPT",
    "STATUS_TRACKING",
    "CORRECTION",
    "ESCALATION",
    "CERTIFICATE_GENERATION",
    "COMPLETED"
]

class StateMachineOrchestrator:
    @staticmethod
    def get_or_create_session(db: Session, session_id: str, channel: str = "Web") -> Tuple[ApplicationState, Application]:
        """
        Retrieves the current application state for a conversation session.
        If none exists, initializes a new state and application.
        """
        # Look for active application state associated with session_id
        # We can map session_id to ApplicationState through an ongoing Application or store it in state_data
        # For simplicity, we search for application states where state_data contains session_id,
        # or we check if there's an application in the DB for this session.
        # Let's search by a unique session lookup.
        app_state = db.query(ApplicationState).filter(
            ApplicationState.state_data["session_id"].astext == session_id
        ).first()

        if app_state:
            app = db.query(Application).filter(Application.id == app_state.application_id).first()
            return app_state, app

        # If not found, create new citizen, application, and application state
        # Create a unique application number INC-2026-XXXXXX
        rand_num = random.randint(100000, 999999)
        app_no = f"INC-2026-{rand_num}"

        # Initialize synthetic service if not present
        inc_service = db.query(Service).filter(Service.id == "income_certificate").first()
        if not inc_service:
            inc_service = Service(
                id="income_certificate",
                name="Income Certificate",
                description="Government Certificate of Annual Family Income",
                required_documents=["identity_proof", "address_proof", "income_proof"],
                fee=50.0,
                processing_days=7
            )
            db.add(inc_service)
            db.commit()

        # Create new application
        app = Application(
            application_no=app_no,
            service_id="income_certificate",
            status="SUBMITTED", # Starting status, we update it as state progresses
            language="en",
            channel=channel
        )
        db.add(app)
        db.commit()
        db.refresh(app)

        # Create application state
        app_state = ApplicationState(
            application_id=app.id,
            current_state="START",
            state_data={
                "session_id": session_id,
                "application_no": app_no,
                "full_name": None,
                "annual_income": None,
                "district": None,
                "consent": None,
                "documents_uploaded": {},
                "ocr_results": {},
                "authenticated": False,
                "payment_status": "PENDING",
                "payment_tx": None,
                "channel_history": [channel],
                "failure_count": 0
            }
        )
        db.add(app_state)
        
        # Log Audit event
        audit = AuditLog(
            actor="system",
            action="APPLICATION_CREATED",
            application_id=app.id,
            channel=channel,
            result="SUCCESS",
            metadata_json={"session_id": session_id, "application_no": app_no}
        )
        db.add(audit)
        
        db.commit()
        db.refresh(app_state)
        
        return app_state, app

    @staticmethod
    def process_state_transition(
        db: Session, 
        app_state: ApplicationState, 
        app: Application, 
        entities: Dict[str, Any], 
        channel: str = "Web"
    ) -> str:
        """
        Executes deterministic rules to transition between states.
        Modifies state_data and application status in-place.
        Returns the new state.
        """
        state_data = dict(app_state.state_data)
        current = app_state.current_state
        
        # Track channel history if citizen switched channels (Section 20: Omnichannel)
        if "channel_history" not in state_data:
            state_data["channel_history"] = [channel]
        elif channel not in state_data["channel_history"]:
            state_data["channel_history"].append(channel)
            app.channel = channel # Update active channel
            # Log channel switch audit log
            audit = AuditLog(
                actor="citizen",
                action="CHANNEL_SWITCHED",
                application_id=app.id,
                channel=channel,
                result="SUCCESS",
                metadata_json={"from": state_data["channel_history"][-2], "to": channel}
            )
            db.add(audit)

        # Update local parameters with newly extracted entities
        for key in ["full_name", "annual_income", "district", "consent", "aadhaar", "otp"]:
            if key in entities and entities[key] is not None:
                state_data[key] = entities[key]

        # 1. State: START
        if current == "START":
            app_state.current_state = "LANGUAGE_SELECTION"
            
        # 2. State: LANGUAGE_SELECTION
        elif current == "LANGUAGE_SELECTION":
            # Language is set by orchestrator based on preferences
            app_state.current_state = "SERVICE_SELECTION"
            
        # 3. State: SERVICE_SELECTION
        elif current == "SERVICE_SELECTION":
            # In our POC, we default to Income Certificate
            app_state.current_state = "INFORMATION_COLLECTION"

        # 4. State: INFORMATION_COLLECTION
        elif current == "INFORMATION_COLLECTION":
            # Check if we have Name, Income, and District
            if state_data.get("full_name") and state_data.get("annual_income") and state_data.get("district"):
                app_state.current_state = "CONSENT"
                
                # Update Citizen model if values exist
                # (For simplicity, we'll link/create citizen record on first submit or info gathering)
                audit = AuditLog(
                    actor="citizen",
                    action="INFORMATION_COLLECTED",
                    application_id=app.id,
                    channel=channel,
                    result="SUCCESS",
                    metadata_json={
                        "full_name": state_data["full_name"],
                        "district": state_data["district"]
                    }
                )
                db.add(audit)

        # 5. State: CONSENT
        elif current == "CONSENT":
            consent = state_data.get("consent")
            if consent is True:
                app_state.current_state = "FORM_VALIDATION"
                # Log Consent
                audit = AuditLog(
                    actor="citizen",
                    action="CONSENT_GIVEN",
                    application_id=app.id,
                    channel=channel,
                    result="SUCCESS",
                    metadata_json={"consent": True}
                )
                db.add(audit)
            elif consent is False:
                # Declined consent. Stay in consent or go to escalation if repeated
                state_data["failure_count"] = state_data.get("failure_count", 0) + 1
                if state_data["failure_count"] >= 3:
                    app_state.current_state = "ESCALATION"
                    state_data["escalation_reason"] = "Consent declined repeatedly"

        # 6. State: FORM_VALIDATION
        elif current == "FORM_VALIDATION":
            # Deterministic business rules
            income = state_data.get("annual_income", 0)
            if income <= 0:
                # Invalid income
                state_data["failure_count"] = state_data.get("failure_count", 0) + 1
                app_state.current_state = "INFORMATION_COLLECTION"
                state_data["annual_income"] = None # Reset
            elif income > 1500000:
                # Non-eligible according to rules (family income must be <= 15 Lakhs for this certificate)
                app_state.current_state = "ESCALATION"
                state_data["escalation_reason"] = "Income exceeds eligibility threshold (> 15 Lakhs)"
            else:
                # Eligibility passed
                app_state.current_state = "DOCUMENT_COLLECTION"
                audit = AuditLog(
                    actor="rules_engine",
                    action="ELIGIBILITY_VERIFIED",
                    application_id=app.id,
                    channel=channel,
                    result="SUCCESS",
                    metadata_json={"annual_income": income}
                )
                db.add(audit)

        # 7. State: DOCUMENT_COLLECTION
        elif current == "DOCUMENT_COLLECTION":
            # Documents are uploaded via API. Once all 3 documents are uploaded, transition.
            docs_uploaded = state_data.get("documents_uploaded", {})
            required_docs = ["identity_proof", "address_proof", "income_proof"]
            
            all_uploaded = True
            for r_doc in required_docs:
                if not docs_uploaded.get(r_doc):
                    all_uploaded = False
                    break
            
            if all_uploaded:
                app_state.current_state = "DOCUMENT_VALIDATION"

        # 8. State: DOCUMENT_VALIDATION
        elif current == "DOCUMENT_VALIDATION":
            # OCR / verification logic. If all validation states are VALIDATED, transition.
            docs_uploaded = state_data.get("documents_uploaded", {})
            ocr_results = state_data.get("ocr_results", {})
            
            all_validated = True
            for doc_type, status in docs_uploaded.items():
                if status != "VALIDATED":
                    all_validated = False
                    if status == "FAILED":
                        # Escalation trigger for bad document OCR confidence (Section 19)
                        app_state.current_state = "ESCALATION"
                        state_data["escalation_reason"] = f"Document OCR validation failed for: {doc_type}"
                        break
            
            if all_validated and app_state.current_state != "ESCALATION":
                app_state.current_state = "AUTHENTICATION"

        # 9. State: AUTHENTICATION
        elif current == "AUTHENTICATION":
            # Mock authentication verification (Aadhaar & OTP)
            if state_data.get("authenticated") is True:
                app_state.current_state = "FEE_CALCULATION"
                # Log success
                audit = AuditLog(
                    actor="auth_adapter",
                    action="AUTHENTICATION_SUCCESS",
                    application_id=app.id,
                    channel=channel,
                    result="SUCCESS",
                    metadata_json={"method": "Aadhaar OTP"}
                )
                db.add(audit)
            elif state_data.get("aadhaar") and state_data.get("otp"):
                # Run validation check: synthetic OTP is 123456
                if state_data["otp"] == "123456" and len(state_data["aadhaar"]) == 12:
                    state_data["authenticated"] = True
                    state_data["failure_count"] = 0
                    app_state.current_state = "FEE_CALCULATION"
                    
                    audit = AuditLog(
                        actor="auth_adapter",
                        action="AUTHENTICATION_SUCCESS",
                        application_id=app.id,
                        channel=channel,
                        result="SUCCESS",
                        metadata_json={"method": "Aadhaar OTP"}
                    )
                    db.add(audit)
                else:
                    state_data["failure_count"] = state_data.get("failure_count", 0) + 1
                    if state_data["failure_count"] >= 3:
                        app_state.current_state = "ESCALATION"
                        state_data["escalation_reason"] = "Aadhaar authentication failed repeatedly"
                    # Reset OTP for retry
                    state_data["otp"] = None

        # 10. State: FEE_CALCULATION
        elif current == "FEE_CALCULATION":
            # Deterministic processing
            state_data["fee"] = 50.0
            app_state.current_state = "PAYMENT"

        # 11. State: PAYMENT
        elif current == "PAYMENT":
            if state_data.get("payment_status") == "SUCCESS":
                app_state.current_state = "SUBMISSION"
                # Log success
                audit = AuditLog(
                    actor="payment_adapter",
                    action="PAYMENT_SUCCESS",
                    application_id=app.id,
                    channel=channel,
                    result="SUCCESS",
                    metadata_json={"amount": 50.0, "tx": state_data.get("payment_tx")}
                )
                db.add(audit)
            elif state_data.get("payment_status") == "FAILED":
                # Do not escalate instantly, allow retry, but log it
                state_data["failure_count"] = state_data.get("failure_count", 0) + 1
                if state_data["failure_count"] >= 3:
                    app_state.current_state = "ESCALATION"
                    state_data["escalation_reason"] = "Payment reconciliation failed repeatedly"

        # 12. State: SUBMISSION
        elif current == "SUBMISSION":
            # Finalize submission
            app.status = "APPROVED" # Automatic approved in POC after validation
            app_state.current_state = "RECEIPT"
            
            audit = AuditLog(
                actor="workflow_engine",
                action="APPLICATION_SUBMITTED",
                application_id=app.id,
                channel=channel,
                result="SUCCESS",
                metadata_json={"app_no": app.application_no}
            )
            db.add(audit)

        # 13. State: RECEIPT
        elif current == "RECEIPT":
            app_state.current_state = "CERTIFICATE_GENERATION"

        # 14. State: CERTIFICATE_GENERATION
        elif current == "CERTIFICATE_GENERATION":
            # Generate PDF
            app_state.current_state = "COMPLETED"
            app.status = "CERTIFICATE_READY"
            
            audit = AuditLog(
                actor="certificate_service",
                action="CERTIFICATE_GENERATED",
                application_id=app.id,
                channel=channel,
                result="SUCCESS",
                metadata_json={"app_no": app.application_no}
            )
            db.add(audit)

        # Handle explicit Correction flow (Section 18)
        if entities.get("correction_field") and entities.get("correction_value"):
            field = entities["correction_field"]
            val = entities["correction_value"]
            if field in ["full_name", "annual_income", "district"]:
                # Save details of correction
                audit = AuditLog(
                    actor="citizen",
                    action="CORRECTION_REQUESTED",
                    application_id=app.id,
                    channel=channel,
                    result="SUCCESS",
                    metadata_json={
                        "field": field,
                        "old_value": state_data.get(field),
                        "new_value": val,
                        "reason": entities.get("correction_reason", "User request")
                    }
                )
                db.add(audit)
                
                # Apply correction
                state_data[field] = val
                
                # Return state back to FORM_VALIDATION to re-verify
                app_state.current_state = "FORM_VALIDATION"
                app.status = "UNDER_REVIEW"

        # Process Escalation if state transitioned to ESCALATION (Section 19)
        if app_state.current_state == "ESCALATION":
            app.status = "REJECTED"
            # Create Escalation row in DB if not already present
            esc_exists = db.query(Escalation).filter(Escalation.application_id == app.id).first()
            if not esc_exists:
                case_id = f"ESC-2026-{random.randint(1000, 9999)}"
                esc = Escalation(
                    application_id=app.id,
                    case_id=case_id,
                    reason=state_data.get("escalation_reason", "Low AI confidence / Policy conflict"),
                    status="PENDING",
                    conversation_context=f"Session: {state_data.get('session_id')} | Full Name: {state_data.get('full_name')} | Income: {state_data.get('annual_income')}",
                    failed_steps=["DOCUMENT_VALIDATION"] if "Document" in state_data.get("escalation_reason", "") else ["AUTHENTICATION"],
                    documents_status=[{"type": k, "status": v} for k, v in state_data.get("documents_uploaded", {}).items()],
                    priority="HIGH"
                )
                db.add(esc)
                
                # Log audit
                audit = AuditLog(
                    actor="workflow_engine",
                    action="ESCALATION_CREATED",
                    application_id=app.id,
                    channel=channel,
                    result="SUCCESS",
                    metadata_json={"case_id": case_id, "reason": esc.reason}
                )
                db.add(audit)

        # Write back changes
        app_state.state_data = state_data
        db.commit()
        
        return app_state.current_state
