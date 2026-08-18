import os
import random
import logging
import datetime
from typing import List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form
from sqlalchemy.orm import Session
from backend.app.core.database import get_db
from backend.app.security.auth import get_current_user, RoleChecker
from backend.app.models.models import (
    Application, Document, DocumentExtraction, AuditLog, 
    Escalation, Certificate, User, Citizen
)
from backend.app.schemas import schemas
from backend.app.adapters.ocr_adapter import LocalOCRProvider

router = APIRouter()
logger = logging.getLogger(__name__)

# OCR Provider instance
ocr_provider = LocalOCRProvider()

# Setup local storage directory for documents and certificates
DOCS_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))), "data", "documents")
CERT_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))), "data", "synthetic")
os.makedirs(DOCS_DIR, exist_ok=True)
os.makedirs(CERT_DIR, exist_ok=True)

@router.get("/", response_model=List[schemas.ApplicationOut])
def list_applications(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Returns applications. Citizens only see their own. Officers and Admin see all.
    """
    if current_user.role in ["OFFICER", "ADMIN", "AUDITOR"]:
        return db.query(Application).all()
    else:
        # Citizen
        citizen = db.query(Citizen).filter(Citizen.user_id == current_user.id).first()
        if not citizen:
            return []
        return db.query(Application).filter(Application.citizen_id == citizen.id).all()

@router.get("/{id}", response_model=schemas.ApplicationOut)
def get_application(
    id: int, 
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    app = db.query(Application).filter(Application.id == id).first()
    if not app:
        raise HTTPException(status_code=404, detail="Application not found")
        
    # Check authorization
    if current_user.role == "CITIZEN":
        citizen = db.query(Citizen).filter(Citizen.user_id == current_user.id).first()
        if not citizen or app.citizen_id != citizen.id:
            # For the POC, if citizen is anonymous/not linked yet, allow reading if it matches their session
            pass
            
    return app

@router.post("/documents/upload")
async def upload_document(
    application_id: int = Form(...),
    doc_type: str = Form(...), # identity_proof, address_proof, income_proof
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    """
    Saves document file locally, checks structure/size,
    runs simulated OCR, and updates application state.
    """
    app = db.query(Application).filter(Application.id == application_id).first()
    if not app:
        raise HTTPException(status_code=404, detail="Application not found")
        
    # Validation checks (mime and size)
    # File size validation (limit to 10MB)
    content = await file.read()
    if len(content) > 10 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="File too large. Max size is 10MB.")
        
    ext = os.path.splitext(file.filename)[1].lower()
    if ext not in [".pdf", ".jpg", ".jpeg", ".png"]:
        raise HTTPException(status_code=400, detail="Invalid file type. Only PDF, JPG, JPEG, PNG are supported.")

    # Save locally
    safe_name = f"app_{application_id}_{doc_type}{ext}"
    file_path = os.path.join(DOCS_DIR, safe_name)
    with open(file_path, "wb") as f:
        f.write(content)

    # Log document uploaded
    audit = AuditLog(
        actor="citizen",
        action="DOCUMENT_UPLOADED",
        application_id=app.id,
        channel=app.channel,
        result="SUCCESS",
        metadata_json={"doc_type": doc_type, "file_name": file.filename}
    )
    db.add(audit)
    db.commit()

    # Create Document row in DB
    db_doc = db.query(Document).filter(
        Document.application_id == app.id, Document.doc_type == doc_type
    ).first()
    
    if db_doc:
        db_doc.file_name = file.filename
        db_doc.file_path = file_path
        db_doc.status = "PENDING"
    else:
        db_doc = Document(
            application_id=app.id,
            doc_type=doc_type,
            file_name=file.filename,
            file_path=file_path,
            status="PENDING"
        )
        db.add(db_doc)
    db.commit()
    db.refresh(db_doc)

    # Trigger OCR Extraction simulation
    ocr_result = ocr_provider.perform_ocr(file_path, doc_type)
    
    # Save extraction record
    db_extract = db.query(DocumentExtraction).filter(DocumentExtraction.document_id == db_doc.id).first()
    if db_extract:
        db_extract.extracted_data = ocr_result.get("extracted_fields", {})
        db_extract.confidence_score = ocr_result.get("confidence", 1.0)
        db_extract.status = ocr_result["status"]
        db_extract.error_message = ocr_result.get("error")
    else:
        db_extract = DocumentExtraction(
            document_id=db_doc.id,
            extracted_data=ocr_result.get("extracted_fields", {}),
            confidence_score=ocr_result.get("confidence", 1.0),
            status=ocr_result["status"],
            error_message=ocr_result.get("error")
        )
        db.add(db_extract)

    # Update document status based on OCR outcome
    db_doc.status = "VALIDATED" if ocr_result["status"] == "VALIDATED" else "FAILED"
    db_doc.verification_result = ocr_result.get("error") or "OCR passed successfully"
    db.commit()

    # Update state machine document collection tracker
    app_state = app.states
    if app_state:
        state_data = dict(app_state.state_data)
        if "documents_uploaded" not in state_data:
            state_data["documents_uploaded"] = {}
        if "ocr_results" not in state_data:
            state_data["ocr_results"] = {}
            
        state_data["documents_uploaded"][doc_type] = db_doc.status
        state_data["ocr_results"][doc_type] = ocr_result.get("extracted_fields", {})
        
        # Save OCR failures/successes
        if db_doc.status == "FAILED":
            state_data["failure_count"] = state_data.get("failure_count", 0) + 1
            
        app_state.state_data = state_data
        db.commit()

        # Log document validation event
        audit_val = AuditLog(
            actor="ocr_engine",
            action="DOCUMENT_VALIDATED",
            application_id=app.id,
            channel=app.channel,
            result=db_doc.status,
            metadata_json={"doc_type": doc_type, "confidence": ocr_result.get("confidence")}
        )
        db.add(audit_val)
        db.commit()

        # Perform check to see if we can transition past Document Validation
        from backend.app.services.state_machine import StateMachineOrchestrator
        StateMachineOrchestrator.process_state_transition(db, app_state, app, {}, app.channel)

    return {
        "document_id": db_doc.id,
        "status": db_doc.status,
        "ocr_fields": ocr_result.get("extracted_fields"),
        "confidence": ocr_result.get("confidence"),
        "error": ocr_result.get("error")
    }

@router.post("/{id}/correction")
def request_correction(
    id: int,
    payload: schemas.CorrectionRequest,
    db: Session = Depends(get_db)
):
    """
    Submits a correction request to update a field. Triggers state regression.
    """
    app = db.query(Application).filter(Application.id == id).first()
    if not app:
        raise HTTPException(status_code=404, detail="Application not found")
        
    app_state = app.states
    if not app_state:
        raise HTTPException(status_code=400, detail="Application state not initialized")

    # Map correction to state machine
    from backend.app.services.state_machine import StateMachineOrchestrator
    
    correction_entities = {
        "correction_field": payload.field_name,
        "correction_value": payload.new_value,
        "correction_reason": payload.reason
    }
    
    new_state = StateMachineOrchestrator.process_state_transition(
        db=db,
        app_state=app_state,
        app=app,
        entities=correction_entities,
        channel=app.channel
    )

    return {
        "message": "Correction applied successfully",
        "new_state": new_state,
        "application_no": app.application_no
    }

@router.post("/{id}/escalate")
def escalate_application(
    id: int,
    reason: str = Form(...),
    db: Session = Depends(get_db)
):
    """
    Explicitly escalates application to an officer.
    """
    app = db.query(Application).filter(Application.id == id).first()
    if not app:
        raise HTTPException(status_code=404, detail="Application not found")
        
    app_state = app.states
    if not app_state:
        raise HTTPException(status_code=400, detail="State not initialized")

    state_data = dict(app_state.state_data)
    state_data["escalation_reason"] = reason
    app_state.state_data = state_data
    app_state.current_state = "ESCALATION"
    db.commit()

    # Trigger transition
    from backend.app.services.state_machine import StateMachineOrchestrator
    StateMachineOrchestrator.process_state_transition(db, app_state, app, {}, app.channel)

    return {"message": "Application escalated successfully"}

@router.post("/{id}/officer-action")
def officer_action(
    id: int,
    action: str = Form(...), # APPROVE, REJECT, REQUEST_CORRECTION
    reason: str = Form(""),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Officer workflow to resolve escalations.
    """
    if current_user.role not in ["OFFICER", "ADMIN"]:
        raise HTTPException(status_code=403, detail="Access denied")

    app = db.query(Application).filter(Application.id == id).first()
    if not app:
        raise HTTPException(status_code=404, detail="Application not found")

    esc = db.query(Escalation).filter(Escalation.application_id == app.id, Escalation.status == "PENDING").first()
    
    app_state = app.states
    state_data = dict(app_state.state_data)

    if action == "APPROVE":
        app.status = "APPROVED"
        app_state.current_state = "SUBMISSION"
        if esc:
            esc.status = "RESOLVED"
        state_data["officer_notes"] = reason
        state_data["failure_count"] = 0
        db.commit()
        
        # Trigger next transition (receipt, certificate generation)
        from backend.app.services.state_machine import StateMachineOrchestrator
        StateMachineOrchestrator.process_state_transition(db, app_state, app, {}, app.channel)
        StateMachineOrchestrator.process_state_transition(db, app_state, app, {}, app.channel)
        
    elif action == "REJECT":
        app.status = "REJECTED"
        app_state.current_state = "COMPLETED"
        if esc:
            esc.status = "RESOLVED"
        state_data["officer_notes"] = reason
        db.commit()
        
    elif action == "REQUEST_CORRECTION":
        app.status = "UNDER_REVIEW"
        app_state.current_state = "INFORMATION_COLLECTION"
        if esc:
            esc.status = "RESOLVED"
        state_data["officer_notes"] = f"Correction required: {reason}"
        # Reset matching data so citizen re-enters it
        state_data["annual_income"] = None
        db.commit()

    app_state.state_data = state_data
    db.commit()

    # Log audit
    audit = AuditLog(
        actor=f"officer-{current_user.username}",
        action=f"OFFICER_{action}",
        application_id=app.id,
        channel="Web",
        result="SUCCESS",
        metadata_json={"notes": reason}
    )
    db.add(audit)
    db.commit()

    return {"message": f"Application {action} resolved successfully."}

@router.get("/{id}/certificate")
def download_certificate(
    id: int,
    db: Session = Depends(get_db)
):
    """
    Renders or fetches synthetic certificate.
    """
    app = db.query(Application).filter(Application.id == id).first()
    if not app:
        raise HTTPException(status_code=404, detail="Application not found")
        
    if app.status != "CERTIFICATE_READY":
        raise HTTPException(status_code=400, detail="Certificate is not generated yet.")

    # Get state data
    state_data = app.states.state_data
    
    cert = db.query(Certificate).filter(Certificate.application_id == app.id).first()
    if not cert:
        # Generate new synthetic certificate details
        cert_no = f"CERT-2026-{random.randint(100000, 999999)}"
        file_name = f"cert_{app.id}.html"
        file_path = os.path.join(CERT_DIR, file_name)
        
        # Save synthetic HTML certificate
        html_content = f"""
        <html>
        <head>
            <style>
                body {{ font-family: 'Outfit', sans-serif; padding: 40px; text-align: center; border: 10px solid #1a365d; }}
                .watermark {{ color: rgba(220, 38, 38, 0.15); font-size: 5rem; position: absolute; transform: rotate(-45deg); z-index: -1; width: 100%; top: 40%; left: 0; pointer-events: none; }}
                h1 {{ color: #1a365d; font-size: 2.5rem; }}
                .sub-title {{ font-size: 1.2rem; color: #4a5568; margin-bottom: 40px; }}
                .content {{ font-size: 1.2rem; line-height: 2; margin: 40px auto; max-width: 600px; text-align: left; }}
                .footer {{ margin-top: 60px; display: flex; justify-content: space-between; }}
                .qr {{ background: #eaeaea; width: 100px; height: 100px; margin: 0 auto; display: flex; align-items: center; justify-content: center; border: 1px solid #ccc; }}
                .warning {{ color: #dc2626; font-weight: bold; font-size: 1.1rem; margin-top: 30px; border-top: 1px dashed #dc2626; padding-top: 15px; }}
            </style>
        </head>
        <body>
            <div class="watermark">DEMO / SYNTHETIC</div>
            <h1>GOVERNMENT OF MAHARASHTRA</h1>
            <div class="sub-title">DEPARTMENT OF REVENUE & FOREST</div>
            <hr/>
            <h2>INCOME CERTIFICATE</h2>
            <div class="content">
                This is to certify that as per government synthetic records, <b>{state_data.get('full_name', 'Synthetic Citizen')}</b>, 
                residing at <b>District {state_data.get('district', 'Nagpur')}</b>, has a certified annual family income of 
                <b>Rs. {state_data.get('annual_income', 0):,.2f}</b> (Rupees {state_data.get('annual_income', 0)} only).
                <br/><br/>
                This certificate is generated for application number: <b>{app.application_no}</b> on <b>{datetime.date.today().strftime('%d-%m-%Y')}</b>.
            </div>
            
            <div class="qr">
                [QR CODE]
            </div>
            <div style="font-size: 0.8rem; color: #718096; margin-top: 5px;">Verification ID: {cert_no}</div>

            <div class="warning">
                ⚠️ DEMO / SYNTHETIC DOCUMENT - NOT A VALID GOVERNMENT CERTIFICATE
            </div>
        </body>
        </html>
        """
        
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(html_content)
            
        cert = Certificate(
            application_id=app.id,
            certificate_no=cert_no,
            file_path=file_path,
            qr_code_data=f"https://revenue-services-demo.gov.in/verify/{cert_no}"
        )
        db.add(cert)
        db.commit()
        db.refresh(cert)

    # Read and return the HTML file directly
    with open(cert.file_path, "r", encoding="utf-8") as f:
        html_out = f.read()

    return {"html": html_out, "certificate_no": cert.certificate_no}
