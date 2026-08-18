import base64
import logging
from typing import Dict, Any, List
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form
from sqlalchemy.orm import Session
from backend.app.core.database import get_db
from backend.app.core.config import settings
from backend.app.schemas import schemas
from backend.app.models.models import Conversation, ConversationMessage
from backend.app.services.state_machine import StateMachineOrchestrator
from backend.app.agents.llm_provider import LocalLLMProvider, CloudLLMProvider

router = APIRouter()
logger = logging.getLogger(__name__)

# Switch LLM Provider by Config (Section 6: Provider Abstraction)
if settings.LLM_PROVIDER == "cloud":
    llm_provider = CloudLLMProvider()
else:
    llm_provider = LocalLLMProvider()

@router.post("/message", response_model=schemas.MessageResponse)
async def process_chat_message(
    payload: schemas.MessageRequest, 
    db: Session = Depends(get_db)
):
    session_id = payload.session_id
    text_input = payload.text or ""
    channel = payload.channel
    
    # 1. Retrieve or create application state machine session
    app_state, app = StateMachineOrchestrator.get_or_create_session(db, session_id, channel=channel)
    
    # 2. Get active conversation row in DB
    conv = db.query(Conversation).filter(Conversation.id == session_id).first()
    if not conv:
        conv = Conversation(
            id=session_id,
            application_id=app.id,
            channel=channel,
            language=payload.language or app.language or "en"
        )
        db.add(conv)
        db.commit()
        db.refresh(conv)

    # If preferred language is forced in request, set it in conversation and application
    if payload.language:
        app.language = payload.language
        conv.language = payload.language
        db.commit()

    # 3. Classify user input data classification (Section 4: Data sovereignty)
    # The classification check will be executed in the LLM provider, 
    # but we store the user message with its classification locally.
    from backend.app.services.data_classification import DataClassificationService
    user_classification = DataClassificationService.classify_content(text_input)

    user_msg = ConversationMessage(
        conversation_id=conv.id,
        role="user",
        content=text_input,
        classification=user_classification
    )
    db.add(user_msg)
    db.commit()

    # 4. Invoke LLM Provider
    result = await llm_provider.process_message(
        text=text_input,
        current_state=app_state.current_state,
        collected_data=app_state.state_data,
        preferred_language=app.language,
        db=db,
        session_id=session_id
    )

    # 5. Execute state transition based on LLM output/entities
    new_state = StateMachineOrchestrator.process_state_transition(
        db=db,
        app_state=app_state,
        app=app,
        entities=result["entities"],
        channel=channel
    )

    # Update app language if detected/changed
    if result.get("language") and result["language"] != app.language:
        app.language = result["language"]
        conv.language = result["language"]
        db.commit()

    # 6. Save LLM Response Message
    bot_msg = ConversationMessage(
        conversation_id=conv.id,
        role="assistant",
        content=result["text"],
        classification="PUBLIC" # Output contains no private information unless echoed
    )
    db.add(bot_msg)
    db.commit()

    # Gather missing fields for UI progress indicators
    missing_fields = []
    state_data = app_state.state_data
    if app_state.current_state in ["INFORMATION_COLLECTION", "CONSENT"]:
        if not state_data.get("full_name"):
            missing_fields.append("full_name")
        if not state_data.get("annual_income"):
            missing_fields.append("annual_income")
        if not state_data.get("district"):
            missing_fields.append("district")
        if state_data.get("consent") is None:
            missing_fields.append("consent")

    return schemas.MessageResponse(
        session_id=session_id,
        text=result["text"],
        state=new_state,
        language=app.language,
        intent=result.get("intent"),
        extracted_data=app_state.state_data,
        missing_fields=missing_fields,
        application_id=app.id,
        is_blocked=result.get("is_blocked", False),
        block_reason=result.get("block_reason")
    )

@router.post("/voice", response_model=schemas.MessageResponse)
async def process_voice_message(
    session_id: str = Form(...),
    channel: str = Form("Web"),
    language: str = Form(None),
    audio: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    """
    Accepts uploaded voice file, runs simulated local Speech-To-Text (STT),
    and redirects the parsed transcript to the conversational orchestrator.
    """
    logger.info(f"Received voice upload for session {session_id}, size: {audio.size} bytes")
    
    # Read/validate audio format
    content = await audio.read()
    
    # Simulating STT (Speech-to-Text) (Section 8: Voice experience)
    # In browser, Web Speech API will handle STT.
    # For server upload, we check the audio name or use mock transcripts.
    # To make this POC fully functional, we detect query words in the file name,
    # or fallback to general demo query sentences.
    file_name = audio.filename.lower()
    transcript = "Hello, I want an income certificate" # default
    
    if "marathi" in file_name or "mr" in file_name:
        transcript = "मला उत्पन्नाचा दाखला काढायचा आहे."
    elif "hindi" in file_name or "hi" in file_name:
        transcript = "मुझे आय प्रमाण पत्र चाहिए"
    elif "status" in file_name:
        transcript = "Check my application status"
    elif "aadhaar" in file_name:
        # Simulate voice dictation of Aadhaar
        transcript = "9999 9999 9999"

    # Forward to the text processor
    request_payload = schemas.MessageRequest(
        session_id=session_id,
        text=transcript,
        channel=channel,
        language=language
    )
    
    return await process_chat_message(request_payload, db)

@router.get("/{session_id}/history", response_model=List[dict])
def get_chat_history(session_id: str, db: Session = Depends(get_db)):
    conv = db.query(Conversation).filter(Conversation.id == session_id).first()
    if not conv:
        return []
        
    messages = db.query(ConversationMessage).filter(
        ConversationMessage.conversation_id == conv.id
    ).order_by(ConversationMessage.timestamp.asc()).all()
    
    return [
        {
            "role": m.role,
            "content": m.content,
            "classification": m.classification,
            "timestamp": m.timestamp
        }
        for m in messages
    ]
