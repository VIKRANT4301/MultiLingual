import re
import logging
from typing import Dict, Any, Tuple
from sqlalchemy.orm import Session
from backend.app.models.models import AuditLog

logger = logging.getLogger(__name__)

# Data Classifications
PUBLIC = "PUBLIC"
INTERNAL = "INTERNAL"
RESTRICTED = "RESTRICTED"
SENSITIVE = "SENSITIVE"

class DataClassificationService:
    # Regex patterns for sensitive citizen data
    AADHAAR_PATTERN = re.compile(r"\b\d{4}[ \-]?\d{4}[ \-]?\d{4}\b")
    PAN_PATTERN = re.compile(r"\b[A-Z]{5}\d{4}[A-Z]\b", re.IGNORECASE)
    PHONE_PATTERN = re.compile(r"\b(?:(?:\+|0{0,2})91[\s\-]?)?[6789]\d{9}\b")
    EMAIL_PATTERN = re.compile(r"\b[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}\b")
    
    # Financial indicators (income certificates deal with financial numbers)
    INCOME_PATTERN = re.compile(r"\b(?:Rs\.?|INR|rupees|रुपये)?\s?\b\d{5,7}\b")

    # Name indicator (heuristics for names in standard patterns "my name is X", "मी X", "मेरा नाम X")
    NAME_PATTERNS = [
        re.compile(r"\b(?:my name is|i am|myself|name is|नाव आहे|नाव|नाम|नाम है)\s+([a-zA-Z\s]{3,30})\b", re.IGNORECASE),
        re.compile(r"\b(?:vikram|patil|sharma|kumar|singh|anil|sanjay|rajesh|priya|amit|sunita|rahul|patel|deshmukh|joshi)\b", re.IGNORECASE)
    ]

    # Address indicator
    ADDRESS_KEYWORDS = ["street", "road", "colony", "nagar", "dist", "district", "village", "taluka", "pincode", "pin code", "गल्ली", "गाव", "शहर", "नगर", "जिल्हा"]

    @classmethod
    def classify_content(cls, content: str) -> str:
        """
        Classifies content as PUBLIC, INTERNAL, RESTRICTED, or SENSITIVE.
        """
        if not content:
            return PUBLIC

        content_str = str(content)

        # 1. Check for SENSITIVE data: Aadhaar or PAN
        if cls.AADHAAR_PATTERN.search(content_str):
            return SENSITIVE
        if cls.PAN_PATTERN.search(content_str):
            return SENSITIVE

        # 2. Check for RESTRICTED data: Name, Phone, Email, Address, Income
        if cls.PHONE_PATTERN.search(content_str):
            return RESTRICTED
        if cls.EMAIL_PATTERN.search(content_str):
            return RESTRICTED
        if cls.INCOME_PATTERN.search(content_str):
            return RESTRICTED
            
        # Check name patterns
        for pattern in cls.NAME_PATTERNS:
            if pattern.search(content_str):
                return RESTRICTED
                
        # Check address keywords
        content_lower = content_str.lower()
        if any(keyword in content_lower for keyword in cls.ADDRESS_KEYWORDS):
            return RESTRICTED

        # 3. INTERNAL heuristics (e.g. references to internal policy IDs, officer codes, database table structures, system logs)
        if "policy_config" in content_lower or "db_schema" in content_lower:
            return INTERNAL

        # 4. Fallback is PUBLIC
        return PUBLIC

    @classmethod
    def evaluate_external_policy(cls, content: str, provider: str = "cloud_llm", db: Session = None, conversation_id: str = None) -> Tuple[bool, str]:
        """
        Evaluates whether content is allowed to be sent to an external provider.
        Returns: (is_allowed, classification_level)
        """
        classification = cls.classify_content(content)
        
        # Policy: RESTRICTED and SENSITIVE must remain local.
        if classification in (RESTRICTED, SENSITIVE):
            reason = f"Block external dispatch: {classification} data detected in payload"
            logger.warning(reason)
            
            # Log audit event if database session is provided
            if db:
                try:
                    audit_event = AuditLog(
                        actor="data_guard",
                        action="EXTERNAL_AI_REQUEST_BLOCKED",
                        channel="System",
                        result="BLOCKED",
                        metadata_json={
                            "event": "external_ai_request_blocked",
                            "classification": classification,
                            "reason": reason,
                            "provider": provider,
                            "conversation_id": conversation_id
                        }
                    )
                    db.add(audit_event)
                    db.commit()
                except Exception as e:
                    logger.error(f"Failed to log audit event: {e}")
                    db.rollback()
            
            return False, classification
            
        return True, classification
