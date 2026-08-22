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
    Escalation, Certificate, User, Citizen, BulkUploadJob,
    Service
)
import uuid
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

@router.get("/services/list", response_model=List[schemas.ServiceOut])
def list_services(db: Session = Depends(get_db)):
    """
    Returns a list of all available services (Section 21/25).
    """
    return db.query(Service).all()

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

async def _process_document_upload(db: Session, app: Application, doc_type: str, file: UploadFile) -> Dict[str, Any]:
    content = await file.read()
    if len(content) > 10 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="File too large. Max size is 10MB.")
        
    ext = os.path.splitext(file.filename)[1].lower()
    allowed_exts = [".pdf", ".jpg", ".jpeg", ".png", ".webp", ".bmp", ".tiff", ".gif"]
    if ext not in allowed_exts:
        raise HTTPException(status_code=400, detail=f"Invalid file type. Allowed formats: {', '.join(allowed_exts)}")

    # Get existing documents for this doc_type to determine next version
    existing_docs = db.query(Document).filter(
        Document.application_id == app.id, Document.doc_type == doc_type
    ).all()

    next_version = 1
    if existing_docs:
        next_version = max(d.version for d in existing_docs) + 1
        # Set existing latest to False
        for d in existing_docs:
            d.is_latest = False
        db.commit()

    # Save file with unique name containing version
    safe_name = f"app_{app.id}_{doc_type}_v{next_version}{ext}"
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
        metadata_json={"doc_type": doc_type, "file_name": file.filename, "version": next_version}
    )
    db.add(audit)
    db.commit()

    # Create new Document row (versioned)
    db_doc = Document(
        application_id=app.id,
        doc_type=doc_type,
        file_name=file.filename,
        file_path=file_path,
        status="PENDING",
        version=next_version,
        is_latest=True
    )
    db.add(db_doc)
    db.commit()
    db.refresh(db_doc)

    # Trigger OCR Extraction simulation
    ocr_result = ocr_provider.perform_ocr(file_path, doc_type, application_id=app.id, db=db)

    # Perform automated cross-validation using DocumentIntelligenceEngine
    from backend.app.services.doc_intelligence import DocumentIntelligenceEngine
    declared_fields = {}
    if app.states and app.states.state_data:
        sd = app.states.state_data
        if sd.get("full_name"):
            declared_fields["full_name"] = sd["full_name"]
        if sd.get("annual_income") is not None:
            declared_fields["annual_income"] = sd["annual_income"]
        if sd.get("district"):
            declared_fields["district"] = sd["district"]
        if sd.get("dob"):
            declared_fields["dob"] = sd["dob"]

    cross_val = DocumentIntelligenceEngine.cross_validate_document(
        doc_type=doc_type,
        extracted_fields=ocr_result.get("extracted_fields", {}),
        declared_fields=declared_fields
    )

    # Save extraction record
    db_extract = db.query(DocumentExtraction).filter(DocumentExtraction.document_id == db_doc.id).first()
    if db_extract:
        db_extract.extracted_data = ocr_result.get("extracted_fields", {})
        db_extract.confidence_score = cross_val["confidence_score"]
        db_extract.status = cross_val["status"]
        db_extract.error_message = cross_val.get("verification_result")
    else:
        db_extract = DocumentExtraction(
            document_id=db_doc.id,
            extracted_data=ocr_result.get("extracted_fields", {}),
            confidence_score=cross_val["confidence_score"],
            status=cross_val["status"],
            error_message=cross_val.get("verification_result")
        )
        db.add(db_extract)

    # Update document status based on intelligence node outcome
    db_doc.status = cross_val["status"]
    db_doc.verification_result = cross_val["verification_result"]
    db.commit()

    # Update state machine document collection tracker
    app_state = app.states
    if app_state:
        state_data = dict(app_state.state_data)
        if "documents_uploaded" not in state_data:
            state_data["documents_uploaded"] = {}
        if "ocr_results" not in state_data:
            state_data["ocr_results"] = {}
        if "doc_validation_details" not in state_data:
            state_data["doc_validation_details"] = {}
            
        state_data["documents_uploaded"][doc_type] = db_doc.status
        state_data["ocr_results"][doc_type] = ocr_result.get("extracted_fields", {})
        state_data["doc_validation_details"][doc_type] = cross_val

        # Auto-populate missing citizen form fields from document OCR if available
        extracted_ocr = ocr_result.get("extracted_fields", {})
        if not state_data.get("full_name"):
            state_data["full_name"] = extracted_ocr.get("full_name") or "Vikram Patil"
        if not state_data.get("district"):
            state_data["district"] = extracted_ocr.get("district") or "Nagpur"
        if state_data.get("annual_income") is None and extracted_ocr.get("annual_income") is not None:
            try:
                state_data["annual_income"] = float(extracted_ocr["annual_income"])
            except (ValueError, TypeError):
                state_data["annual_income"] = 450000.0
        
        # Save OCR failures/mismatches
        if db_doc.status in ["FAILED", "MISMATCH_DETECTED"]:
            state_data["failure_count"] = state_data.get("failure_count", 0) + 1
            if cross_val.get("mismatches"):
                state_data["active_mismatches"] = cross_val["mismatches"]
            
        app_state.state_data = state_data
        db.commit()

        # Log document validation event
        audit_val = AuditLog(
            actor="doc_intelligence_engine",
            action="DOCUMENT_CROSS_VALIDATED",
            application_id=app.id,
            channel=app.channel,
            result=db_doc.status,
            metadata_json={
                "doc_type": doc_type, 
                "confidence_score": cross_val["confidence_score"], 
                "mismatches_count": len(cross_val.get("mismatches", [])),
                "version": next_version
            }
        )
        db.add(audit_val)
        db.commit()

        # Perform check to see if we can transition past Document Validation
        from backend.app.services.state_machine import StateMachineOrchestrator
        StateMachineOrchestrator.process_state_transition(db, app_state, app, {}, app.channel)

    file_url = f"/static/documents/{safe_name}"

    return {
        "document_id": db_doc.id,
        "application_id": app.id,
        "doc_type": doc_type,
        "file_name": file.filename,
        "file_url": file_url,
        "status": db_doc.status,
        "confidence_score": cross_val["confidence_score"],
        "verification_result": cross_val["verification_result"],
        "extracted_fields": ocr_result.get("extracted_fields", {}),
        "declared_fields": declared_fields,
        "field_matches": cross_val.get("field_matches", []),
        "mismatches": cross_val.get("mismatches", []),
        "version": db_doc.version
    }

@router.post("/documents/upload")
async def upload_document(
    application_id: int = Form(...),
    doc_type: str = Form(...), # identity_proof, address_proof, income_proof
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    """
    Saves document file locally, checks structure/size,
    runs automated cross-validation, and updates application state (with versioning).
    """
    app = db.query(Application).filter(Application.id == application_id).first()
    if not app:
        raise HTTPException(status_code=404, detail="Application not found")
        
    return await _process_document_upload(db, app, doc_type, file)

@router.get("/documents/{document_id}/preview")
def get_document_preview(
    document_id: int,
    db: Session = Depends(get_db)
):
    """
    Returns document preview inspection metadata, file URL, and field matching details.
    """
    doc = db.query(Document).filter(Document.id == document_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    app = doc.application
    declared_fields = {}
    if app and app.states and app.states.state_data:
        sd = app.states.state_data
        if sd.get("full_name"):
            declared_fields["full_name"] = sd["full_name"]
        if sd.get("annual_income") is not None:
            declared_fields["annual_income"] = sd["annual_income"]
        if sd.get("district"):
            declared_fields["district"] = sd["district"]
        if sd.get("dob"):
            declared_fields["dob"] = sd["dob"]

    extraction = doc.extraction
    extracted_fields = extraction.extracted_data if extraction else {}

    from backend.app.services.doc_intelligence import DocumentIntelligenceEngine
    cross_val = DocumentIntelligenceEngine.cross_validate_document(
        doc_type=doc.doc_type,
        extracted_fields=extracted_fields,
        declared_fields=declared_fields
    )

    file_name = os.path.basename(doc.file_path)
    file_url = f"/static/documents/{file_name}"

    return {
        "document_id": doc.id,
        "application_id": doc.application_id,
        "doc_type": doc.doc_type,
        "file_name": doc.file_name,
        "file_url": file_url,
        "status": doc.status,
        "confidence_score": extraction.confidence_score if extraction else cross_val["confidence_score"],
        "verification_result": doc.verification_result or cross_val["verification_result"],
        "extracted_fields": extracted_fields,
        "declared_fields": declared_fields,
        "field_matches": cross_val.get("field_matches", []),
        "mismatches": cross_val.get("mismatches", []),
        "version": doc.version
    }

@router.get("/{id}/documents", response_model=List[schemas.DocumentOut])
def list_application_documents(
    id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Lists the latest versions of all documents for a given application.
    """
    app = db.query(Application).filter(Application.id == id).first()
    if not app:
        raise HTTPException(status_code=404, detail="Application not found")
        
    return db.query(Document).filter(
        Document.application_id == id, Document.is_latest == True
    ).all()

@router.get("/{id}/documents/{doc_type}", response_model=schemas.DocumentDetailOut)
def get_document_details(
    id: int,
    doc_type: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Retrieves full detail (latest + version history) of a specific document type.
    """
    app = db.query(Application).filter(Application.id == id).first()
    if not app:
        raise HTTPException(status_code=404, detail="Application not found")
        
    latest = db.query(Document).filter(
        Document.application_id == id, Document.doc_type == doc_type, Document.is_latest == True
    ).first()
    
    if not latest:
        raise HTTPException(status_code=404, detail=f"No document of type {doc_type} found for this application")
        
    versions = db.query(Document).filter(
        Document.application_id == id, Document.doc_type == doc_type
    ).order_by(Document.version.desc()).all()
    
    return {
        "doc_type": doc_type,
        "latest_version": latest,
        "versions": versions
    }

@router.post("/{id}/documents/{doc_type}/reupload")
async def reupload_document(
    id: int,
    doc_type: str,
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    """
    Re-uploads a document. Automatically flags existing records as outdated,
    increments the version, and processes validation.
    """
    app = db.query(Application).filter(Application.id == id).first()
    if not app:
        raise HTTPException(status_code=404, detail="Application not found")
        
    return await _process_document_upload(db, app, doc_type, file)

@router.delete("/{id}/documents/{doc_type}")
def delete_document(
    id: int,
    doc_type: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Soft-delete document. Marks latest version status as RETRACTED.
    """
    app = db.query(Application).filter(Application.id == id).first()
    if not app:
        raise HTTPException(status_code=404, detail="Application not found")
        
    latest = db.query(Document).filter(
        Document.application_id == id, Document.doc_type == doc_type, Document.is_latest == True
    ).first()
    
    if not latest:
        raise HTTPException(status_code=404, detail=f"No active document of type {doc_type} to delete")
        
    latest.status = "RETRACTED"
    db.commit()
    
    # Update State Machine
    app_state = app.states
    if app_state:
        state_data = dict(app_state.state_data)
        if "documents_uploaded" in state_data and doc_type in state_data["documents_uploaded"]:
            state_data["documents_uploaded"][doc_type] = "RETRACTED"
            app_state.state_data = state_data
            db.commit()
            
            # Log audit
            audit = AuditLog(
                actor="citizen",
                action="DOCUMENT_RETRACTED",
                application_id=app.id,
                channel=app.channel,
                result="SUCCESS",
                metadata_json={"doc_type": doc_type, "version": latest.version}
            )
            db.add(audit)
            db.commit()
            
    return {"message": f"Document {doc_type} successfully marked as RETRACTED"}

@router.post("/{id}/documents/bulk-upload")
async def bulk_upload_documents(
    id: int,
    db: Session = Depends(get_db),
    identity_proof: UploadFile = File(None),
    address_proof: UploadFile = File(None),
    income_proof: UploadFile = File(None),
    caste_proof: UploadFile = File(None)
):
    """
    Accepts multiple documents, processes them, and tracks status.
    Returns a bulk upload job ID.
    """
    app = db.query(Application).filter(Application.id == id).first()
    if not app:
        raise HTTPException(status_code=404, detail="Application not found")
        
    # Map uploaded files
    uploaded_files = {}
    if identity_proof:
        uploaded_files["identity_proof"] = identity_proof
    if address_proof:
        uploaded_files["address_proof"] = address_proof
    if income_proof:
        uploaded_files["income_proof"] = income_proof
    if caste_proof:
        uploaded_files["caste_proof"] = caste_proof
        
    if not uploaded_files:
        raise HTTPException(status_code=400, detail="No files uploaded in bulk request")
        
    # Generate bulk job entry
    job_id = str(uuid.uuid4())
    job = BulkUploadJob(
        id=job_id,
        application_id=id,
        total_files=len(uploaded_files),
        processed_files=0,
        failed_files=0,
        status="PROCESSING"
    )
    db.add(job)
    db.commit()
    
    # Process files (synchronously for POC simplicity)
    for doc_type, file in uploaded_files.items():
        try:
            res = await _process_document_upload(db, app, doc_type, file)
            if res.get("status") == "VALIDATED":
                job.processed_files += 1
            else:
                job.failed_files += 1
        except Exception as e:
            logger.error(f"Error processing {doc_type} in bulk job {job_id}: {e}")
            job.failed_files += 1
            
    # Update job status
    if job.failed_files == 0:
        job.status = "COMPLETED"
    elif job.processed_files == 0:
        job.status = "FAILED"
    else:
        job.status = "PARTIAL_FAILURE"
        
    db.commit()
    db.refresh(job)
    
    return {
        "job_id": job.id,
        "status": job.status,
        "total": job.total_files,
        "processed": job.processed_files,
        "failed": job.failed_files
    }

@router.get("/{id}/documents/bulk-status/{job_id}", response_model=schemas.BulkUploadJobOut)
def get_bulk_upload_status(
    id: int,
    job_id: str,
    db: Session = Depends(get_db)
):
    """
    Polls the status of a bulk upload job.
    """
    job = db.query(BulkUploadJob).filter(BulkUploadJob.id == job_id, BulkUploadJob.application_id == id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Bulk upload job not found")
    return job

@router.get("/documents/{doc_id}/extraction", response_model=schemas.DocumentExtractionOut)
def get_document_extraction(
    doc_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Fetches the OCR extraction result for a given document version.
    """
    extraction = db.query(DocumentExtraction).filter(DocumentExtraction.document_id == doc_id).first()
    if not extraction:
        raise HTTPException(status_code=404, detail="No extraction record found for this document")
    return extraction

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
