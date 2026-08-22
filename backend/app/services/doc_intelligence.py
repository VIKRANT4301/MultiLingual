import re
import logging
from typing import Dict, Any, List, Tuple, Optional
from difflib import SequenceMatcher

logger = logging.getLogger(__name__)

class DocumentIntelligenceEngine:
    """
    Intelligent cross-validation engine that compares extracted OCR/Vision data
    against citizen's declared inputs. Computes fuzzy similarity, financial variance,
    composite confidence scores, and mismatch alerts.
    """

    @staticmethod
    def normalize_string(val: Optional[str]) -> str:
        if not val:
            return ""
        # Remove extra spaces, convert to lowercase, strip punctuation
        cleaned = re.sub(r"[^\w\s]", "", str(val)).lower().strip()
        return " ".join(cleaned.split())

    @staticmethod
    def compute_fuzzy_similarity(str1: str, str2: str) -> float:
        """
        Computes token sort ratio similarity between two strings (0.0 to 1.0).
        Handles Indian name token order variations (e.g., 'Vikram Patil' vs 'Patil Vikram').
        """
        n1 = DocumentIntelligenceEngine.normalize_string(str1)
        n2 = DocumentIntelligenceEngine.normalize_string(str2)

        if not n1 or not n2:
            return 0.0

        if n1 == n2:
            return 1.0

        # Token sort similarity
        tokens1 = " ".join(sorted(n1.split()))
        tokens2 = " ".join(sorted(n2.split()))
        
        ratio = SequenceMatcher(None, tokens1, tokens2).ratio()
        return round(ratio, 2)

    @staticmethod
    def parse_numeric(val: Any) -> Optional[float]:
        """
        Parses numeric amounts from string or number.
        Handles INR numbers like '4,50,000', '4.5 lakh', 'Rs. 450000'.
        """
        if val is None:
            return None

        if isinstance(val, (int, float)):
            return float(val)

        val_str = str(val).lower().replace(",", "").strip()

        # Check for 'lakh' or 'लाख'
        lakh_match = re.search(r"(\d+(?:\.\d+)?)\s*(?:lakh|लाख|lakhs)", val_str)
        if lakh_match:
            try:
                return float(lakh_match.group(1)) * 100000.0
            except ValueError:
                pass

        # Check for digits
        digits = re.findall(r"\d+(?:\.\d+)?", val_str)
        if digits:
            try:
                return float(digits[0])
            except ValueError:
                pass

        return None

    @staticmethod
    def compute_numeric_variance(val1: Any, val2: Any) -> Tuple[float, float]:
        """
        Calculates variance percentage and similarity score for numbers (e.g. annual income).
        Returns: (variance_percent, similarity_score)
        """
        num1 = DocumentIntelligenceEngine.parse_numeric(val1)
        num2 = DocumentIntelligenceEngine.parse_numeric(val2)

        if num1 is None or num2 is None:
            return 0.0, 0.0

        if num1 == num2:
            return 0.0, 1.0

        denom = max(abs(num1), 1.0)
        variance = abs(num1 - num2) / denom

        if variance <= 0.05:  # Within 5% variance
            similarity = 1.0
        elif variance <= 0.15:  # Within 15% variance
            similarity = 0.7
        elif variance <= 0.30:  # Within 30% variance
            similarity = 0.4
        else:
            similarity = 0.0

        return round(variance * 100, 1), similarity

    @classmethod
    def cross_validate_document(
        cls, 
        doc_type: str, 
        extracted_fields: Dict[str, Any], 
        declared_fields: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Cross-checks extracted document fields against citizen declared fields.
        Supports both existing form input comparison and automatic field population.
        Returns detailed matching breakdown, confidence score, and mismatch alerts.
        """
        matches: List[Dict[str, Any]] = []
        mismatches: List[Dict[str, Any]] = []
        field_scores: List[float] = []

        # 1. Full Name Verification / Auto-fill
        extracted_name = extracted_fields.get("full_name") or extracted_fields.get("applicant_name")
        declared_name = declared_fields.get("full_name")

        if extracted_name:
            if declared_name:
                sim = cls.compute_fuzzy_similarity(extracted_name, declared_name)
                field_scores.append(sim)
                match_status = "MATCH" if sim >= 0.75 else "MISMATCH"
                
                matches.append({
                    "field_name": "full_name",
                    "declared": declared_name,
                    "extracted": extracted_name,
                    "similarity": sim,
                    "status": match_status,
                    "explanation": f"Form name '{declared_name}' vs Document name '{extracted_name}' ({int(sim*100)}% match)"
                })

                if sim < 0.75:
                    mismatches.append({
                        "field_name": "full_name",
                        "issue": f"Name mismatch: Declared '{declared_name}' vs Document '{extracted_name}' ({int(sim*100)}% similarity)",
                        "declared_val": declared_name,
                        "extracted_val": extracted_name
                    })
            else:
                # Auto-filled from document
                field_scores.append(1.0)
                matches.append({
                    "field_name": "full_name",
                    "declared": extracted_name,
                    "extracted": extracted_name,
                    "similarity": 1.0,
                    "status": "AUTO_FILLED",
                    "explanation": f"Auto-filled applicant name '{extracted_name}' from document OCR"
                })

        # 2. Annual Income Verification / Auto-fill
        extracted_income = extracted_fields.get("annual_income") or extracted_fields.get("income")
        declared_income = declared_fields.get("annual_income")

        if extracted_income is not None:
            parsed_ext = cls.parse_numeric(extracted_income)
            if declared_income is not None:
                parsed_dec = cls.parse_numeric(declared_income)
                variance_pct, sim = cls.compute_numeric_variance(declared_income, extracted_income)
                field_scores.append(sim)
                match_status = "MATCH" if sim >= 0.7 else "MISMATCH"

                matches.append({
                    "field_name": "annual_income",
                    "declared": parsed_dec,
                    "extracted": parsed_ext,
                    "variance_percent": variance_pct,
                    "similarity": sim,
                    "status": match_status,
                    "explanation": f"Form income ₹{parsed_dec:,.2f} vs Document income ₹{parsed_ext:,.2f} ({variance_pct}% variance)"
                })

                if sim < 0.7:
                    mismatches.append({
                        "field_name": "annual_income",
                        "issue": f"Income variance detected: Declared ₹{parsed_dec:,.2f} vs Document ₹{parsed_ext:,.2f} ({variance_pct}% difference)",
                        "declared_val": parsed_dec,
                        "extracted_val": parsed_ext
                    })
            else:
                # Auto-filled from document
                field_scores.append(1.0)
                matches.append({
                    "field_name": "annual_income",
                    "declared": parsed_ext,
                    "extracted": parsed_ext,
                    "similarity": 1.0,
                    "status": "AUTO_FILLED",
                    "explanation": f"Auto-filled annual income ₹{parsed_ext:,.2f} from document OCR"
                })

        # 3. Date of Birth Verification / Auto-fill
        extracted_dob = extracted_fields.get("dob")
        declared_dob = declared_fields.get("dob")

        if extracted_dob:
            if declared_dob:
                sim = cls.compute_fuzzy_similarity(extracted_dob, declared_dob)
                field_scores.append(sim)
                match_status = "MATCH" if sim >= 0.9 else "MISMATCH"

                matches.append({
                    "field_name": "dob",
                    "declared": declared_dob,
                    "extracted": extracted_dob,
                    "similarity": sim,
                    "status": match_status,
                    "explanation": f"Form DOB '{declared_dob}' vs Document DOB '{extracted_dob}'"
                })

                if sim < 0.9:
                    mismatches.append({
                        "field_name": "dob",
                        "issue": f"DOB mismatch: Declared '{declared_dob}' vs Document '{extracted_dob}'",
                        "declared_val": declared_dob,
                        "extracted_val": extracted_dob
                    })
            else:
                field_scores.append(1.0)
                matches.append({
                    "field_name": "dob",
                    "declared": extracted_dob,
                    "extracted": extracted_dob,
                    "similarity": 1.0,
                    "status": "AUTO_FILLED",
                    "explanation": f"Auto-filled Date of Birth '{extracted_dob}' from document OCR"
                })

        # 4. District / Address Verification / Auto-fill
        extracted_district = extracted_fields.get("district") or extracted_fields.get("address")
        declared_district = declared_fields.get("district")

        if extracted_district:
            if declared_district:
                sim = cls.compute_fuzzy_similarity(extracted_district, declared_district)
                field_scores.append(sim)
                match_status = "MATCH" if sim >= 0.6 else "MISMATCH"
                matches.append({
                    "field_name": "district",
                    "declared": declared_district,
                    "extracted": extracted_district,
                    "similarity": sim,
                    "status": match_status,
                    "explanation": f"Form district '{declared_district}' vs Document '{extracted_district}'"
                })

                if sim < 0.6:
                    mismatches.append({
                        "field_name": "district",
                        "issue": f"District mismatch: Form input '{declared_district}' vs Document text '{extracted_district}'",
                        "declared_val": declared_district,
                        "extracted_val": extracted_district
                    })
            else:
                field_scores.append(1.0)
                matches.append({
                    "field_name": "district",
                    "declared": extracted_district,
                    "extracted": extracted_district,
                    "similarity": 1.0,
                    "status": "AUTO_FILLED",
                    "explanation": f"Auto-filled district '{extracted_district}' from document OCR"
                })

        # 5. Additional Key Certificate Extractions (Caste, Father Name, Issue Date)
        for extra_key, label in [("caste", "Caste / Category"), ("father_name", "Father's Name"), ("issue_date", "Issue Date")]:
            val = extracted_fields.get(extra_key)
            if val:
                matches.append({
                    "field_name": extra_key,
                    "declared": val,
                    "extracted": val,
                    "similarity": 1.0,
                    "status": "AUTO_FILLED",
                    "explanation": f"Extracted {label} '{val}' from document"
                })

        # Base confidence from OCR engine confidence metric
        ocr_base_conf = float(extracted_fields.get("_ocr_confidence", 0.95))

        if field_scores:
            avg_field_score = sum(field_scores) / len(field_scores)
            composite_confidence = round((0.3 * ocr_base_conf) + (0.7 * avg_field_score), 2)
        else:
            composite_confidence = round(ocr_base_conf, 2)

        overall_status = "VALIDATED"
        if mismatches:
            overall_status = "MISMATCH_DETECTED" if composite_confidence >= 0.6 else "REVIEW_REQUIRED"

        verification_result = "All extracted fields match declared application data."
        if any(m.get("status") == "AUTO_FILLED" for m in matches):
            verification_result = "Document validated & missing application fields auto-filled successfully."
        if mismatches:
            verification_result = f"Attention: {len(mismatches)} field discrepancy(ies) detected. Please review."

        return {
            "status": overall_status,
            "confidence_score": composite_confidence,
            "verification_result": verification_result,
            "field_matches": matches,
            "mismatches": mismatches
        }
