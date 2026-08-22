import os
import random
import logging
from typing import Dict, Any, Tuple

logger = logging.getLogger(__name__)

class OCRProvider:
    def perform_ocr(self, file_path: str, doc_type: str) -> Dict[str, Any]:
        raise NotImplementedError

class LocalOCRProvider(OCRProvider):
    def perform_ocr(self, file_path: str, doc_type: str, application_id: int = None, db = None) -> Dict[str, Any]:
        """
        Locally simulates OCR processing. Inspects file name and returns
        structured synthetic fields based on the doc_type, optionally matching
        the form inputs to test dynamic accuracy scoring and mismatches.
        """
        logger.info(f"Performing local OCR on file: {file_path} (Type: {doc_type}, AppId: {application_id})")
        
        # Simple file format checks
        ext = os.path.splitext(file_path)[1].lower()
        if ext not in [".pdf", ".jpg", ".jpeg", ".png"]:
            return {
                "status": "FAILED",
                "error": "Unsupported file format. Only PDF, JPG, JPEG, and PNG are allowed.",
                "confidence": 0.0,
                "extracted_fields": {}
            }

        # Retrieve form data from db if available
        form_name = "Amit Singh"
        form_district = "Pune"
        form_income = 450000.0
        
        if application_id and db:
            try:
                from backend.app.models.models import ApplicationState
                app_state = db.query(ApplicationState).filter(ApplicationState.application_id == application_id).first()
                if app_state and app_state.state_data:
                    state_data = app_state.state_data
                    if state_data.get("full_name"):
                        form_name = state_data["full_name"]
                    if state_data.get("district"):
                        form_district = state_data["district"]
                    if state_data.get("annual_income") is not None:
                        form_income = float(state_data["annual_income"])
            except Exception as e:
                logger.error(f"Error loading state_data in OCR provider: {e}")

        # Set confidence score
        confidence = round(random.uniform(0.92, 0.99), 2)
        extracted = {}
        status = "VALIDATED"
        error = None
        
        file_lower = file_path.lower()
        is_mismatch = "mismatch" in file_lower or "invalid" in file_lower or "bad" in file_lower

        if doc_type == "identity_proof":
            extracted = {
                "document_name": "Aadhaar Card",
                "full_name": "Vikram Patil" if is_mismatch else form_name,
                "dob": "15-08-1988" if is_mismatch else "12-05-2002",
                "gender": "Male"
            }
        elif doc_type == "address_proof":
            extracted = {
                "document_name": "Utility Bill",
                "address": "Flat 302, Green Avenue, Nagpur" if is_mismatch else f"Flat 101, Shanti Nagar, {form_district}",
                "pincode": "440010" if is_mismatch else "411001"
            }
        elif doc_type == "income_proof":
            extracted = {
                "document_name": "Salary Slip / Form 16",
                "annual_income": 950000.0 if is_mismatch else form_income,
                "employer": "Tech Corp Pvt Ltd"
            }
        elif doc_type == "caste_proof":
            extracted = {
                "document_name": "Caste Certificate",
                "full_name": "Vikram Patil" if is_mismatch else form_name,
                "dob": "12-05-2003" if is_mismatch else "12-05-2002"
            }
        else:
            status = "FAILED"
            error = f"Unknown doc_type {doc_type} for OCR simulation"
            logger.warning(error)

        return {
            "status": status,
            "confidence": confidence,
            "extracted_fields": extracted,
            "error": error
        }

class CloudOCRProvider(OCRProvider):
    def __init__(self):
        self.local_ocr = LocalOCRProvider()

    def perform_ocr(self, file_path: str, doc_type: str, application_id: int = None, db = None) -> Dict[str, Any]:
        """
        Mock cloud OCR provider. Under a real deployment, this would dispatch
        to Google Cloud Vision or Azure Form Recognizer, but would be restricted
        by our Data Sovereignty Guard if personal identifiers are in the document metadata.
        """
        # Fallback to local
        logger.info("Cloud OCR not configured or blocked. Redirecting to local OCR provider.")
        return self.local_ocr.perform_ocr(file_path, doc_type, application_id, db)
