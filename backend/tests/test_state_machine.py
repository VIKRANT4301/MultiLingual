import time
from backend.app.services.state_machine import StateMachineOrchestrator
from backend.app.core.database import SessionLocal

def test_session_creation():
    db = SessionLocal()
    try:
        session_id = f"test-sess-create-{int(time.time())}"
        app_state, app = StateMachineOrchestrator.get_or_create_session(db, session_id)
        
        assert app_state is not None
        assert app is not None
        assert app_state.current_state == "START"
        assert app_state.state_data["session_id"] == session_id
    finally:
        db.close()

def test_state_transitions():
    db = SessionLocal()
    try:
        session_id = f"test-sess-trans-{int(time.time())}"
        
        # First message selects service and transitions to INFORMATION_COLLECTION
        app_state, app = StateMachineOrchestrator.get_or_create_session(db, session_id)
        state = StateMachineOrchestrator.process_state_transition(
            db=db,
            app_state=app_state,
            app=app,
            entities={"user_text": "I want to apply for Domicile Certificate"},
            channel="Web"
        )
        assert state == "INFORMATION_COLLECTION"
        
        # Check that service_id is successfully captured in DB state
        db.refresh(app)
        assert app.service_id == "domicile_certificate"
    finally:
        db.close()
