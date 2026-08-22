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
        allowed_exts = [".pdf", ".jpg", ".jpeg", ".png", ".webp", ".bmp", ".tiff", ".gif"]
        if ext not in allowed_exts:
            return {
                "status": "FAILED",
                "error": f"Unsupported file format. Allowed formats: {', '.join(allowed_exts)}",
                "confidence": 0.0,
                "extracted_fields": {}
            }

        # Retrieve form data from db if available
        form_name = None
        form_district = None
        form_income = None
        
        if application_id and db:
            try:
                from backend.app.models.models import ApplicationState
                app_state = db.query(ApplicationState).filter(ApplicationState.application_id == application_id).first()
                if app_state and app_state.state_data:
                    state_data = app_state.state_data
                    if state_data.get("full_name") and len(state_data["full_name"].strip()) > 3 and state_data["full_name"].lower() not in ["hii", "hi", "hello", "test"]:
                        form_name = state_data["full_name"]
                    if state_data.get("district"):
                        form_district = state_data["district"]
                    if state_data.get("annual_income") is not None:
                        form_income = float(state_data["annual_income"])
            except Exception as e:
                logger.error(f"Error loading state_data in OCR provider: {e}")

        # Real document extracted attributes
        doc_full_name = form_name if (form_name and "kunal" in form_name.lower()) else "Shri Krunal Ashok Wandhare"
        doc_district = "Nagpur" # Document text specifies District Nagpur, Taluka Bhiwapur
        doc_income = form_income if (form_income and form_income > 0) else 450000.0

        # Set confidence score
        confidence = round(random.uniform(0.94, 0.99), 2)
        extracted = {}
        status = "VALIDATED"
        error = None
        
        file_lower = file_path.lower()
        is_mismatch = "mismatch" in file_lower or "invalid" in file_lower or "bad" in file_lower

        if doc_type == "identity_proof":
            extracted = {
                "document_name": "Aadhaar Card",
                "full_name": "Vikram Patil" if is_mismatch else doc_full_name,
                "dob": "15-08-1988" if is_mismatch else "07-06-2005",
                "gender": "Male",
                "district": doc_district,
                "_ocr_confidence": confidence
            }
        elif doc_type == "address_proof":
            extracted = {
                "document_name": "Utility Bill / Ration Card",
                "full_name": doc_full_name,
                "address": "Flat 302, Green Avenue, Nagpur" if is_mismatch else f"Village Salebhatti, Taluka Bhiwapur, {doc_district}",
                "district": doc_district,
                "pincode": "441201",
                "_ocr_confidence": confidence
            }
        elif doc_type == "income_proof":
            extracted = {
                "document_name": "Salary Slip / Form 16",
                "full_name": doc_full_name,
                "annual_income": 950000.0 if is_mismatch else doc_income,
                "employer": "Tech Corp Pvt Ltd",
                "_ocr_confidence": confidence
            }
        elif doc_type == "caste_proof":
            extracted = {
                "document_name": "Caste Certificate (FORM-8)",
                "full_name": "Vikram Patil" if is_mismatch else doc_full_name,
                "father_name": "Shri Ashok Vithoba Wandhare",
                "caste": "SUTAR (Serial No 174)",
                "category": "OBC",
                "village": "Salebhatti",
                "taluka": "Bhiwapur",
                "district": doc_district,
                "issue_date": "18/08/2018",
                "case_no": "194",
                "_ocr_confidence": confidence
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
