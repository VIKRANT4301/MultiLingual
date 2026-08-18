import logging
from sqlalchemy.orm import Session
from backend.app.services.state_machine import StateMachineOrchestrator
from backend.app.agents.llm_provider import LocalLLMProvider

logger = logging.getLogger(__name__)

class WhatsAppAdapter:
    def __init__(self):
        self.llm = LocalLLMProvider()

    async def receive_message(self, db: Session, phone_number: str, text: str) -> dict:
        """
        Simulates receiving a WhatsApp text from a citizen.
        Uses phone number as a unique seed to map/create a session ID.
        """
        # Seed sessionId based on phone
        session_id = f"wa-session-{phone_number}"
        logger.info(f"[WhatsApp Adapter] Received message from {phone_number}: {text}")
        
        # 1. Retrieve or create application state
        app_state, app = StateMachineOrchestrator.get_or_create_session(db, session_id, channel="WhatsApp")
        
        # 2. Process conversation message through LLM and State Machine
        state_data = dict(app_state.state_data)
        
        # Process the input text with Local LLM (always local-first for messaging info)
        result = await self.llm.process_message(
            text=text,
            current_state=app_state.current_state,
            collected_data=state_data,
            preferred_language=app.language,
            db=db,
            session_id=session_id
        )
        
        # Transition State
        new_state = StateMachineOrchestrator.process_state_transition(
            db=db,
            app_state=app_state,
            app=app,
            entities=result["entities"],
            channel="WhatsApp"
        )
        
        # Format WhatsApp text reply
        response_text = result["text"]
        
        return {
            "to": phone_number,
            "reply_text": response_text,
            "session_id": session_id,
            "application_no": app.application_no,
            "state": new_state
        }

class IVRAdapter:
    @staticmethod
    def handle_call_status_check(db: Session, caller_id: str, app_no: str = None) -> dict:
        """
        Simulates an IVR citizen status check call.
        """
        session_id = f"ivr-session-{caller_id}"
        logger.info(f"[IVR Adapter] Call received from {caller_id}")
        
        # Check if caller has an active application in the system
        # In a real IVR, we lookup by caller_id (which is their phone) or prompt for application number digits
        # Let's search by application number or matching caller phone
        app = None
        if app_no:
            app = db.query(Application).filter(Application.application_no == app_no.upper()).first()
        else:
            # Look up by phone if available in citizen records
            # Since this is a POC, we search for the latest active application
            app = db.query(Application).order_by(Application.created_at.desc()).first()

        if not app:
            return {
                "tts_text": "We could not find any active application matching your number. Please speak with an officer.",
                "action": "TRANSFER_TO_AGENT"
            }
            
        # Log IVR status check audit event
        audit = AuditLog(
            actor=f"ivr-{caller_id}",
            action="STATUS_CHECKED_IVR",
            application_id=app.id,
            channel="IVR",
            result="SUCCESS",
            metadata_json={"caller_id": caller_id}
        )
        db.add(audit)
        db.commit()
        
        # Format audio response text (Hindi, Marathi, or English)
        status_text = {
            "SUBMITTED": "under validation",
            "UNDER_REVIEW": "under manual review by an officer",
            "DOCUMENT_VERIFICATION": "verifying uploaded certificates",
            "APPROVED": "approved and pending certificate download",
            "CERTIFICATE_READY": "completed and ready for download",
            "REJECTED": "rejected, please check your online dashboard"
        }.get(app.status, "received")
        
        tts_reply = f"Hello. Your application number {app.application_no} status is {status_text}."
        
        return {
            "tts_text": tts_reply,
            "application_no": app.application_no,
            "status": app.status,
            "action": "HANGUP"
        }
