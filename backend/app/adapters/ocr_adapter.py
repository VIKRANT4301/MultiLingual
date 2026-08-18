import os
import random
import logging
from typing import Dict, Any, Tuple

logger = logging.getLogger(__name__)

class OCRProvider:
    def perform_ocr(self, file_path: str, doc_type: str) -> Dict[str, Any]:
        raise NotImplementedError

class LocalOCRProvider(OCRProvider):
    def perform_ocr(self, file_path: str, doc_type: str) -> Dict[str, Any]:
        """
        Locally simulates OCR processing. Inspects file name and returns
        structured synthetic fields based on the doc_type.
        """
        logger.info(f"Performing local OCR on file: {file_path} (Type: {doc_type})")
        
        # Simple file format checks
        ext = os.path.splitext(file_path)[1].lower()
        if ext not in [".pdf", ".jpg", ".jpeg", ".png"]:
            return {
                "status": "FAILED",
                "error": "Unsupported file format. Only PDF, JPG, JPEG, and PNG are allowed.",
                "confidence": 0.0,
                "extracted_fields": {}
            }

        # Simulating processing delay and security/virus validation
        # Returns synthetic extracted data
        confidence = round(random.uniform(0.85, 0.99), 2)
        
        # We can construct realistic extracted fields based on doc_type
        extracted = {}
        status = "VALIDATED"
        
        # Force validation failure for a specific demo filename to test failure recovery (Section 36)
        if "invalid" in file_path.lower() or "bad" in file_path.lower():
            return {
                "status": "FAILED",
                "error": "Document image resolution is too low. Name and address unreadable.",
                "confidence": 0.42,
                "extracted_fields": {}
            }

        if doc_type == "identity_proof":
            extracted = {
                "document_name": "Aadhaar Card",
                "full_name": "Vikram Patil",
                "dob": "15-08-1988",
                "gender": "Male"
            }
        elif doc_type == "address_proof":
            extracted = {
                "document_name": "Utility Bill",
                "address": "Flat 302, Green Avenue, Nagpur",
                "pincode": "440010"
            }
        elif doc_type == "income_proof":
            extracted = {
                "document_name": "Salary Slip / Form 16",
                "annual_income": 450000.0,
                "employer": "Tech Corp Pvt Ltd"
            }
        else:
            status = "FAILED"
            logger.warning(f"Unknown doc_type {doc_type} for OCR simulation")

        return {
            "status": status,
            "confidence": confidence,
            "extracted_fields": extracted,
            "error": None
        }

class CloudOCRProvider(OCRProvider):
    def __init__(self):
        self.local_ocr = LocalOCRProvider()

    def perform_ocr(self, file_path: str, doc_type: str) -> Dict[str, Any]:
        """
        Mock cloud OCR provider. Under a real deployment, this would dispatch
        to Google Cloud Vision or Azure Form Recognizer, but would be restricted
        by our Data Sovereignty Guard if personal identifiers are in the document metadata.
        """
        # Fallback to local
        logger.info("Cloud OCR not configured or blocked. Redirecting to local OCR provider.")
        return self.local_ocr.perform_ocr(file_path, doc_type)
