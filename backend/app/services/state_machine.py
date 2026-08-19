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
        from sqlalchemy import func
        app_state = db.query(ApplicationState).filter(
            func.json_extract(ApplicationState.state_data, '$.session_id') == session_id
        ).first()

        if app_state:
            app = db.query(Application).filter(Application.id == app_state.application_id).first()
            
            # Redis Hot Cache Simulation: Sync session state to Vault
            from backend.app.services.task_queue import RedisContextVault
            RedisContextVault.set(session_id, app_state.state_data)
            
            return app_state, app

        # If not found, create new citizen, application, and application state
        rand_num = random.randint(100000, 999999)
        app_no = f"NCL-2026-{rand_num}" # Default to NCL for our demonstration scenario

        # Create new application
        app = Application(
            application_no=app_no,
            service_id="obc_ncl_certificate", # Defaults to OBC/NCL Certificate for our demo
            status="SUBMITTED",
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
                "failure_count": 0,
                "readiness_score": 0,
                "suspended_ncl_app_id": None,
                "dob_mismatch_resolved": False,
                "dob_mismatch_detected": False
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
        
        # Redis Cache write
        from backend.app.services.task_queue import RedisContextVault
        RedisContextVault.set(session_id, app_state.state_data)
        
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
        Executes database-driven rules to transition between states.
        Modifies state_data and application status in-place.
        Returns the new state.
        """
        state_data = dict(app_state.state_data)
        current = app_state.current_state
        
        # Track channel history for Omnichannel Context Persistence
        if "channel_history" not in state_data:
            state_data["channel_history"] = [channel]
        elif channel not in state_data["channel_history"]:
            state_data["channel_history"].append(channel)
            app.channel = channel # Update active channel
            
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

        # Fetch Service Details dynamically from DB
        service = db.query(Service).filter(Service.id == app.service_id).first()
        required_docs = service.required_documents if service else ["identity_proof", "address_proof"]

        # 1. State: START
        if current == "START":
            app_state.current_state = "LANGUAGE_SELECTION"
            
        # 2. State: LANGUAGE_SELECTION
        elif current == "LANGUAGE_SELECTION":
            app_state.current_state = "SERVICE_SELECTION"
            
        # 3. State: SERVICE_SELECTION
        elif current == "SERVICE_SELECTION":
            if entities.get("intent") in ["OBC_NCL_CERTIFICATE", "INCOME_CERTIFICATE"] or "ncl" in str(entities).lower():
                # Allow dynamic service switching
                if "income" in str(entities).lower() and "ncl" not in str(entities).lower():
                    app.service_id = "income_certificate"
                else:
                    app.service_id = "obc_ncl_certificate"
                db.commit()
            app_state.current_state = "INFORMATION_COLLECTION"

        # 4. State: INFORMATION_COLLECTION
        elif current == "INFORMATION_COLLECTION":
            # Check if name and district are present (income is checked dynamically depending on service)
            if state_data.get("full_name") and state_data.get("district"):
                if app.service_id == "obc_ncl_certificate" and state_data.get("annual_income") is None:
                    # Let the LLM ask for income or documents next
                    pass
                else:
                    app_state.current_state = "CONSENT"
                
                # Log audit
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
                state_data["failure_count"] = state_data.get("failure_count", 0) + 1
                if state_data["failure_count"] >= 3:
                    app_state.current_state = "ESCALATION"
                    state_data["escalation_reason"] = "Consent declined repeatedly"

        # 6. State: FORM_VALIDATION
        elif current == "FORM_VALIDATION":
            # Database-driven rules validation
            from backend.app.models.models import ServiceRule
            rules = db.query(ServiceRule).filter(ServiceRule.service_id == app.service_id).all()
            
            rule_failed = False
            error_msg = ""
            for rule in rules:
                # Simple rule evaluator (e.g. check if income threshold is breached)
                if "annual_income <= 800000" in rule.rule_condition:
                    income = float(state_data.get("annual_income") or 0.0)
                    if income > 800000.0:
                        rule_failed = True
                        error_msg = rule.error_message
                        break
                elif "annual_income <= 1500000" in rule.rule_condition:
                    income = float(state_data.get("annual_income") or 0.0)
                    if income > 1500000.0:
                        rule_failed = True
                        error_msg = rule.error_message
                        break

            if rule_failed:
                app_state.current_state = "ESCALATION"
                state_data["escalation_reason"] = f"Eligibility Rule Blocked: {error_msg}"
            else:
                app_state.current_state = "DOCUMENT_COLLECTION"
                audit = AuditLog(
                    actor="rules_engine",
                    action="ELIGIBILITY_VERIFIED",
                    application_id=app.id,
                    channel=channel,
                    result="SUCCESS",
                    metadata_json={"service_id": app.service_id}
                )
                db.add(audit)

        # 7. State: DOCUMENT_COLLECTION
        elif current == "DOCUMENT_COLLECTION":
            # Handle Self-Recovering Prerequisite Loop if user states they lack Income Proof
            if app.service_id == "obc_ncl_certificate" and entities.get("lacks_income_proof") is True:
                # Transition to PREREQUISITE_PROMPT
                app_state.current_state = "PREREQUISITE_PROMPT"
                state_data["lacks_income_proof"] = True
            else:
                docs_uploaded = state_data.get("documents_uploaded", {})
                all_uploaded = True
                for r_doc in required_docs:
                    if not docs_uploaded.get(r_doc):
                        all_uploaded = False
                        break
                
                if all_uploaded:
                    app_state.current_state = "DOCUMENT_VALIDATION"

        # 8. State: PREREQUISITE_PROMPT
        elif current == "PREREQUISITE_PROMPT":
            # Awaiting user response: "Haan, start karo"
            if entities.get("confirm_prerequisite") is True:
                # Save NCL application ID
                ncl_id = app.id
                
                # Suspend NCL, create nested Income Certificate
                rand_num = random.randint(100000, 999999)
                inc_app_no = f"INC-2026-{rand_num}"
                
                nested_app = Application(
                    application_no=inc_app_no,
                    service_id="income_certificate",
                    status="SUBMITTED",
                    language=app.language,
                    channel=app.channel
                )
                db.add(nested_app)
                db.commit()
                db.refresh(nested_app)

                # Create application state for nested flow
                nested_state = ApplicationState(
                    application_id=nested_app.id,
                    current_state="INFORMATION_COLLECTION", # Skip greetings, start collecting info
                    state_data={
                        "session_id": state_data["session_id"],
                        "application_no": inc_app_no,
                        "full_name": state_data.get("full_name"),
                        "district": state_data.get("district"),
                        "annual_income": 450000.0, # Seed a valid value
                        "consent": True,
                        "documents_uploaded": {},
                        "ocr_results": {},
                        "authenticated": False,
                        "payment_status": "PENDING",
                        "payment_tx": None,
                        "channel_history": state_data["channel_history"],
                        "failure_count": 0,
                        "readiness_score": 0,
                        "suspended_ncl_app_id": ncl_id # Link parent application to return back later
                    }
                )
                db.add(nested_state)
                db.commit()

                # Set active pointer to the nested app state
                app_state.current_state = "NESTED_INCOME_FLOW"
                state_data["nested_income_app_id"] = nested_app.id
                state_data["suspended_ncl_app_id"] = ncl_id
                
                # Log audit
                audit = AuditLog(
                    actor="workflow_engine",
                    action="PREREQUISITE_LOOP_STARTED",
                    application_id=app.id,
                    channel=channel,
                    result="SUCCESS",
                    metadata_json={"nested_app_no": inc_app_no}
                )
                db.add(audit)
            elif entities.get("confirm_prerequisite") is False:
                # Cancelled. Go to escalation
                app_state.current_state = "ESCALATION"
                state_data["escalation_reason"] = "User declined starting prerequisite Income Certificate flow"

        # 9. State: NESTED_INCOME_FLOW
        elif current == "NESTED_INCOME_FLOW":
            # Wait for nested application to finish. In this mock, we automatically process and complete it
            # once user submits their details.
            # Let's say user uploads salary slips or system auto-approves it
            nested_id = state_data.get("nested_income_app_id")
            nested_app = db.query(Application).filter(Application.id == nested_id).first()
            
            if nested_app:
                # Auto-approve Income Certificate for POC demo
                nested_app.status = "APPROVED"
                
                # Create synthetic certificate record
                from backend.app.models.models import Certificate
                cert = db.query(Certificate).filter(Certificate.application_id == nested_app.id).first()
                if not cert:
                    cert_no = f"CERT-INC-2026-{random.randint(1000, 9999)}"
                    cert = Certificate(
                        application_id=nested_app.id,
                        certificate_no=cert_no,
                        file_path=f"/static/certificates/{cert_no.lower()}.pdf",
                    )
                    db.add(cert)
                
                db.commit()

                # Link new certificate back to NCL as income_proof
                parent_id = state_data.get("suspended_ncl_app_id")
                parent_app = db.query(Application).filter(Application.id == parent_id).first()
                parent_state = parent_app.states if parent_app else None
                
                if parent_state:
                    parent_state_data = dict(parent_state.state_data)
                    parent_state_data["documents_uploaded"]["income_proof"] = "VALIDATED"
                    parent_state_data["ocr_results"]["income_proof"] = {
                        "document_name": "Income Certificate",
                        "annual_income": 450000.0,
                        "certificate_no": cert.certificate_no
                    }
                    
                    # Fill other documents as uploaded for the demo sequence
                    parent_state_data["documents_uploaded"]["identity_proof"] = "VALIDATED"
                    parent_state_data["documents_uploaded"]["caste_proof"] = "VALIDATED"
                    parent_state_data["documents_uploaded"]["address_proof"] = "VALIDATED"
                    
                    # Transition parent NCL flow directly back to resume at Form validation
                    parent_state.current_state = "DOCUMENT_VALIDATION"
                    parent_state.state_data = parent_state_data
                    db.commit()
                    
                    # Swap current active pointer back to NCL
                    app_state.current_state = "DOCUMENT_VALIDATION"
                    # Sync state data with parent data, but preserve session and resume variables
                    state_data = parent_state_data
                    state_data["prerequisite_completed"] = True
                    state_data["readiness_score"] = 92 # Ready to submit matching our second image checklist
                    
                    audit = AuditLog(
                        actor="workflow_engine",
                        action="PREREQUISITE_LOOP_COMPLETED",
                        application_id=parent_app.id,
                        channel=channel,
                        result="SUCCESS",
                        metadata_json={"certificate_no": cert.certificate_no}
                    )
                    db.add(audit)
                    db.commit()

        # 10. State: DOCUMENT_VALIDATION
        elif current == "DOCUMENT_VALIDATION":
            # Document validation & Evidence Graph check
            docs_uploaded = state_data.get("documents_uploaded", {})
            ocr_results = state_data.get("ocr_results", {})
            
            all_validated = True
            for doc_type, status in docs_uploaded.items():
                if status != "VALIDATED":
                    all_validated = False
            
            if all_validated:
                # Scenario 1: Non-Creamy Layer DOB Mismatch (Image 1 check)
                # Verify Aadhaar DOB vs Caste Proof DOB
                dob_aadhaar = ocr_results.get("identity_proof", {}).get("dob")
                dob_caste = ocr_results.get("caste_proof", {}).get("dob")
                
                # If there's a mismatch and user hasn't resolved it yet, trigger DOB correction
                if dob_aadhaar and dob_caste and dob_aadhaar != dob_caste and not state_data.get("dob_mismatch_resolved"):
                    app_state.current_state = "DOB_MISMATCH_PROMPT"
                    state_data["dob_mismatch_detected"] = True
                    state_data["readiness_score"] = 87 # Needs Minor Fix score matching diagram 1
                else:
                    # Proceed to AUTHENTICATION
                    app_state.current_state = "AUTHENTICATION"
                    # Set readiness score: if prerequisite completed, it's 92/100 (Image 2) else 100/100
                    if state_data.get("prerequisite_completed"):
                        state_data["readiness_score"] = 92
                    else:
                        state_data["readiness_score"] = 100

        # 11. State: DOB_MISMATCH_PROMPT
        elif current == "DOB_MISMATCH_PROMPT":
            # Waiting for DOB confirmation. If user specifies "12-05-2002" or similar
            if entities.get("dob_resolution") == "12-05-2002" or entities.get("confirm_dob") is True:
                state_data["dob_mismatch_resolved"] = True
                # Correct it in Caste proof record as well
                if "caste_proof" in state_data["ocr_results"]:
                    state_data["ocr_results"]["caste_proof"]["dob"] = "12-05-2002"
                app_state.current_state = "AUTHENTICATION"
                state_data["readiness_score"] = 100
                
                audit = AuditLog(
                    actor="citizen",
                    action="DOB_MISMATCH_CORRECTED",
                    application_id=app.id,
                    channel=channel,
                    result="SUCCESS",
                    metadata_json={"resolved_dob": "12-05-2002"}
                )
                db.add(audit)
                db.commit()

        # 12. State: AUTHENTICATION
        elif current == "AUTHENTICATION":
            # Verify OTP
            if state_data.get("authenticated") is True:
                app_state.current_state = "FEE_CALCULATION"
            elif state_data.get("otp") in ["741286", "123456"]: # Support OTPs from diagrams
                state_data["authenticated"] = True
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
            elif state_data.get("aadhaar") and state_data.get("otp"):
                state_data["failure_count"] = state_data.get("failure_count", 0) + 1
                if state_data["failure_count"] >= 3:
                    app_state.current_state = "ESCALATION"
                    state_data["escalation_reason"] = "OTP verification failed repeatedly"
                state_data["otp"] = None

        # 13. State: FEE_CALCULATION
        elif current == "FEE_CALCULATION":
            # Compute fee based on database model
            state_data["fee"] = service.fee if service else 50.0
            app_state.current_state = "PAYMENT"

        # 14. State: PAYMENT
        elif current == "PAYMENT":
            if state_data.get("payment_status") == "SUCCESS":
                app_state.current_state = "SUBMISSION"
            elif state_data.get("payment_status") == "FAILED":
                state_data["failure_count"] = state_data.get("failure_count", 0) + 1
                if state_data["failure_count"] >= 3:
                    app_state.current_state = "ESCALATION"
                    state_data["escalation_reason"] = "Payment verification failed repeatedly"

        # 15. State: SUBMISSION
        elif current == "SUBMISSION":
            app.status = "APPROVED"
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

        # 16. State: RECEIPT
        elif current == "RECEIPT":
            app_state.current_state = "CERTIFICATE_GENERATION"

        # 17. State: CERTIFICATE_GENERATION
        elif current == "CERTIFICATE_GENERATION":
            app_state.current_state = "COMPLETED"
            app.status = "CERTIFICATE_READY"
            
            # Generate PDF
            from backend.app.models.models import Certificate
            cert_no = f"CERT-NCL-2026-{random.randint(1000, 9999)}"
            cert = Certificate(
                application_id=app.id,
                certificate_no=cert_no,
                file_path=f"/static/certificates/{cert_no.lower()}.pdf"
            )
            db.add(cert)
            
            audit = AuditLog(
                actor="certificate_service",
                action="CERTIFICATE_GENERATED",
                application_id=app.id,
                channel=channel,
                result="SUCCESS",
                metadata_json={"cert_no": cert_no}
            )
            db.add(audit)

        # Process corrections if explicitly requested
        if entities.get("correction_field") and entities.get("correction_value"):
            field = entities["correction_field"]
            val = entities["correction_value"]
            if field in ["full_name", "annual_income", "district"]:
                state_data[field] = val
                app_state.current_state = "FORM_VALIDATION"
                app.status = "UNDER_REVIEW"

        # Process Escalation triggers
        if app_state.current_state == "ESCALATION":
            app.status = "REJECTED"
            from backend.app.models.models import Escalation
            esc_exists = db.query(Escalation).filter(Escalation.application_id == app.id).first()
            if not esc_exists:
                case_id = f"ESC-2026-{random.randint(1000, 9999)}"
                esc = Escalation(
                    application_id=app.id,
                    case_id=case_id,
                    reason=state_data.get("escalation_reason", "AI confidence check failed"),
                    status="PENDING",
                    conversation_context=f"Session: {state_data.get('session_id')}",
                    failed_steps=["DOCUMENT_VALIDATION"],
                    documents_status=[{"type": k, "status": v} for k, v in state_data.get("documents_uploaded", {}).items()],
                    priority="HIGH"
                )
                db.add(esc)
                
                audit = AuditLog(
                    actor="workflow_engine",
                    action="ESCALATION_CREATED",
                    application_id=app.id,
                    channel=channel,
                    result="SUCCESS",
                    metadata_json={"case_id": case_id, "reason": esc.reason}
                )
                db.add(audit)

        # Write back changes and sync to Redis cache vault
        app_state.state_data = state_data
        db.commit()
        
        from backend.app.services.task_queue import RedisContextVault
        RedisContextVault.set(state_data["session_id"], state_data)

        return app_state.current_state
