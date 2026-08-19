import re
import json
import logging
from typing import Dict, Any, Tuple
from sqlalchemy.orm import Session
from backend.app.models.models import AuditLog

logger = logging.getLogger(__name__)

class OPAPolicyEngine:
    # Compile regexes for Aadhaar, PAN, Phone, Email
    AADHAAR_PATTERN = re.compile(r"\b\d{4}[ \-]?\d{4}[ \-]?\d{4}\b")
    PAN_PATTERN = re.compile(r"\b[A-Z]{5}\d{4}[A-Z]\b", re.IGNORECASE)
    PHONE_PATTERN = re.compile(r"\b(?:(?:\+|0{0,2})91[\s\-]?)?[6789]\d{9}\b")
    EMAIL_PATTERN = re.compile(r"\b[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}\b")

    # Rego-like policy rule definition simulated in Python
    POLICY_REGO = """
    package play.sovereignty

    default allow = false
    default action = "LOCAL_ONLY"

    # Rule: Allow cloud processing if no PII and data is not classified as RESTRICTED/SENSITIVE
    allow {
        not pii_detected
        not restricted_data
    }

    action = "CLOUD_APPROVED" {
        allow
    }
    """

    @classmethod
    def evaluate_policy(cls, text: str, context: Dict[str, Any], db: Session = None, session_id: str = None) -> Dict[str, Any]:
        """
        OPA Decision Simulation. Evaluates policies based on inputs and session context.
        Returns: {
            "allow": bool,
            "action": str,       # CLOUD_APPROVED or LOCAL_ONLY
            "reasons": list,     # list of policy violation reasons
            "policy_package": "play.sovereignty"
        }
        """
        reasons = []
        pii_fields = []
        content_to_check = f"Text: {text} | Context: {json.dumps(context)}"

        # 1. Check for Aadhaar
        if cls.AADHAAR_PATTERN.search(content_to_check):
            reasons.append("Sovereignty violation: Aadhaar (12-digit UID) detected in payload")
            pii_fields.append("Aadhaar")

        # 2. Check for PAN
        if cls.PAN_PATTERN.search(content_to_check):
            reasons.append("Sovereignty violation: PAN card number detected in payload")
            pii_fields.append("PAN")

        # 3. Check for Phone
        if cls.PHONE_PATTERN.search(content_to_check):
            reasons.append("Privacy violation: Citizen mobile number detected in payload")
            pii_fields.append("Phone")

        # 4. Check for Email
        if cls.EMAIL_PATTERN.search(content_to_check):
            reasons.append("Privacy violation: Citizen email address detected in payload")
            pii_fields.append("Email")

        # 5. Check if names or financial figures are defined in context
        if context.get("full_name") or context.get("annual_income"):
            reasons.append("Data classification constraint: Active citizen profile identifiers (Name/Income) loaded")
            pii_fields.append("ProfileMetadata")

        allow = len(reasons) == 0
        action = "CLOUD_APPROVED" if allow else "LOCAL_ONLY"

        # Log policy evaluation result in DB Audit logs if available
        if db and not allow:
            try:
                audit = AuditLog(
                    actor="opa_policy_engine",
                    action="POLICY_EVALUATION_DENIED",
                    channel="System",
                    result="BLOCKED",
                    metadata_json={
                        "policy_package": "play.sovereignty",
                        "allow": allow,
                        "action": action,
                        "reasons": reasons,
                        "pii_fields": pii_fields,
                        "session_id": session_id
                    }
                )
                db.add(audit)
                db.commit()
            except Exception as e:
                logger.error(f"Failed to write policy audit log: {e}")
                db.rollback()

        return {
            "allow": allow,
            "action": action,
            "reasons": reasons,
            "policy_package": "play.sovereignty"
        }
