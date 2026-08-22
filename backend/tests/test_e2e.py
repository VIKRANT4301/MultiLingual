import time
from backend.app.services.state_machine import StateMachineOrchestrator
from backend.app.core.database import SessionLocal

def test_income_certificate_e2e_journey():
    db = SessionLocal()
    session_id = f"test-e2e-income-{int(time.time())}"
    try:
        # Step 1: Initialize session (START state)
        app_state, app = StateMachineOrchestrator.get_or_create_session(db, session_id)
        assert app_state.current_state == "START"
        
        # Step 2: First message starts application and selects Income Certificate
        state = StateMachineOrchestrator.process_state_transition(
            db=db,
            app_state=app_state,
            app=app,
            entities={"user_text": "I want to apply for Income Certificate"},
            channel="Web"
        )
        assert state == "INFORMATION_COLLECTION"
        assert app.service_id == "income_certificate"
        
        # Step 3: User provides full name
        state = StateMachineOrchestrator.process_state_transition(
            db=db,
            app_state=app_state,
            app=app,
            entities={"full_name": "Abhay Sathawane"},
            channel="Web"
        )
        assert state == "INFORMATION_COLLECTION"
        assert app_state.state_data["full_name"] == "Abhay Sathawane"
        
        # Step 4: User provides district
        state = StateMachineOrchestrator.process_state_transition(
            db=db,
            app_state=app_state,
            app=app,
            entities={"district": "Nagpur"},
            channel="Web"
        )
        # Should stay in INFORMATION_COLLECTION because income is required but not yet provided!
        assert state == "INFORMATION_COLLECTION"
        assert app_state.state_data["district"] == "Nagpur"
        assert app_state.state_data.get("annual_income") is None
        
        # Step 5: User provides annual family income
        state = StateMachineOrchestrator.process_state_transition(
            db=db,
            app_state=app_state,
            app=app,
            entities={"annual_income": 450000.0},
            channel="Web"
        )
        # With name, district, and income collected, it should transition to CONSENT!
        assert state == "CONSENT"
        assert app_state.state_data["annual_income"] == 450000.0
        
        # Step 6: User gives consent
        state = StateMachineOrchestrator.process_state_transition(
            db=db,
            app_state=app_state,
            app=app,
            entities={"consent": True},
            channel="Web"
        )
        # Consent transitions to FORM_VALIDATION, then rules run and transition to DOCUMENT_COLLECTION
        assert state == "DOCUMENT_COLLECTION"
        assert app_state.state_data["consent"] is True
        
        # Step 7: Upload documents and run mock OCR validation
        # Set documents as validated and mock ocr data matching the declared income
        state_data = dict(app_state.state_data)
        state_data["documents_uploaded"] = {
            "identity_proof": "VALIDATED",
            "address_proof": "VALIDATED",
            "income_proof": "VALIDATED"
        }
        state_data["ocr_results"] = {
            "identity_proof": {"full_name": "Abhay Sathawane", "dob": "12-05-2002"},
            "address_proof": {"address": "123 Sector Nagpur"},
            "income_proof": {"annual_income": 450000.0}
        }
        app_state.state_data = state_data
        db.commit()
        
        # Trigger transition check to transition from DOCUMENT_COLLECTION -> DOCUMENT_VALIDATION -> AUTHENTICATION
        state = StateMachineOrchestrator.process_state_transition(
            db=db, app_state=app_state, app=app, entities={}, channel="Web"
        )
        assert state == "AUTHENTICATION"
        
        # Step 8: User authenticates with OTP
        state = StateMachineOrchestrator.process_state_transition(
            db=db,
            app_state=app_state,
            app=app,
            entities={"otp": "123456"},
            channel="Web"
        )
        # Authentication success transitions to FEE_CALCULATION, calculates fee (50.0), and goes to PAYMENT
        assert state == "PAYMENT"
        assert app_state.state_data["fee"] == 50.0
        
        # Step 9: Citizen pays mock fee
        state_data = dict(app_state.state_data)
        state_data["payment_status"] = "SUCCESS"
        app_state.state_data = state_data
        db.commit()
        
        state = StateMachineOrchestrator.process_state_transition(
            db=db, app_state=app_state, app=app, entities={}, channel="Web"
        )
        # Payment success transitions to SUBMISSION -> RECEIPT -> CERTIFICATE_GENERATION -> COMPLETED
        assert state == "COMPLETED"
        
        # Reload application to verify final status
        db.refresh(app)
        assert app.status == "CERTIFICATE_READY"
        print("[OK] End-to-end Income Certificate flow passed successfully!")
    finally:
        db.close()
