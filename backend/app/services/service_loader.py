import os
import yaml
import logging
from typing import Dict, Any, List, Tuple, Optional

logger = logging.getLogger(__name__)

class ServiceLoader:
    """
    Dynamic Loader & Rule Engine for Certificate Service YAML Policies.
    Provides cached access to service schemas, fields, document groups, fees, SLAs,
    eligibility checks, and prerequisite dependency requirements.
    """

    _SERVICES_DIR = os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))),
        "services"
    )
    _cache: Dict[str, Dict[str, Any]] = {}

    @classmethod
    def get_services_dir(cls) -> str:
        return cls._SERVICES_DIR

    @classmethod
    def load_service(cls, service_id: str) -> Dict[str, Any]:
        """
        Load and cache a service YAML policy by service_id.
        """
        if service_id in cls._cache:
            return cls._cache[service_id]

        file_name = f"{service_id}.yaml" if not service_id.endswith(".yaml") else service_id
        file_path = os.path.join(cls._SERVICES_DIR, file_name)

        if not os.path.exists(file_path):
            # Fallback check for service_id without '_certificate' or vice versa
            alt_id = f"{service_id}_certificate" if not service_id.endswith("_certificate") else service_id.replace("_certificate", "")
            alt_path = os.path.join(cls._SERVICES_DIR, f"{alt_id}.yaml")
            if os.path.exists(alt_path):
                file_path = alt_path
            else:
                logger.warning(f"Service policy file not found: {file_path}. Returning default schema.")
                return cls._get_default_schema(service_id)

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f)
                cls._cache[service_id] = data
                return data
        except Exception as e:
            logger.error(f"Error reading YAML file {file_path}: {e}")
            return cls._get_default_schema(service_id)

    @classmethod
    def get_required_fields(cls, service_id: str) -> List[Dict[str, Any]]:
        """
        Returns list of required field definition dicts for the service.
        """
        service_data = cls.load_service(service_id)
        return service_data.get("required_fields", [])

    @classmethod
    def get_required_documents(cls, service_id: str) -> Dict[str, Any]:
        """
        Returns required document groups dict for the service.
        """
        service_data = cls.load_service(service_id)
        return service_data.get("required_document_groups", {})

    @classmethod
    def get_fee(cls, service_id: str) -> float:
        """
        Returns government fee in INR (default 50.0).
        """
        service_data = cls.load_service(service_id)
        fee_info = service_data.get("fee", {})
        if isinstance(fee_info, dict):
            return float(fee_info.get("amount") or 50.0)
        elif isinstance(fee_info, (int, float)):
            return float(fee_info)
        return 50.0

    @classmethod
    def get_processing_days(cls, service_id: str) -> int:
        """
        Returns official processing SLA in working days (default 7).
        """
        service_data = cls.load_service(service_id)
        return int(service_data.get("processing_days", 7))

    @classmethod
    def get_dependency_rules(cls, service_id: str) -> List[Dict[str, Any]]:
        """
        Returns prerequisite certificate requirements list.
        """
        service_data = cls.load_service(service_id)
        dep_rules = service_data.get("dependency_rules", {})
        return dep_rules.get("required_prerequisites", [])

    @classmethod
    def check_eligibility(cls, service_id: str, state_data: Dict[str, Any], language: str = "en") -> Tuple[bool, Optional[str]]:
        """
        Validates state_data values against eligibility_rules.
        Returns (is_eligible, failure_reason_message).
        """
        service_data = cls.load_service(service_id)
        rules = service_data.get("eligibility_rules", [])

        for r in rules:
            field_name = r.get("field")
            if not field_name:
                continue

            val = state_data.get(field_name)
            if val is None:
                continue

            try:
                numeric_val = float(val)
                cond = r.get("condition")
                target_val = float(r.get("value", 0))

                if cond == "lte" and numeric_val > target_val:
                    err_msg = r.get("error_message", {})
                    if isinstance(err_msg, dict):
                        msg = err_msg.get(language, err_msg.get("en", "Income threshold exceeded."))
                    else:
                        msg = str(err_msg)
                    return False, msg

                elif cond == "gte" and numeric_val < target_val:
                    err_msg = r.get("error_message", {})
                    if isinstance(err_msg, dict):
                        msg = err_msg.get(language, err_msg.get("en", "Minimum requirement not met."))
                    else:
                        msg = str(err_msg)
                    return False, msg
            except (ValueError, TypeError):
                pass

        return True, None

    @classmethod
    def list_all_services(cls) -> List[Dict[str, Any]]:
        """
        Scans services directory and returns summary list of all available YAML services.
        """
        services = []
        if not os.path.exists(cls._SERVICES_DIR):
            return services

        for f in os.listdir(cls._SERVICES_DIR):
            if f.endswith(".yaml") or f.endswith(".yml"):
                sid = f.rsplit(".", 1)[0]
                data = cls.load_service(sid)
                services.append({
                    "id": sid,
                    "name": data.get("name", {}),
                    "description": data.get("description", {}),
                    "fee": cls.get_fee(sid),
                    "processing_days": cls.get_processing_days(sid)
                })
        return services

    @classmethod
    def _get_default_schema(cls, service_id: str) -> Dict[str, Any]:
        """
        Fallback schema if YAML file is missing.
        """
        return {
            "id": service_id,
            "name": {"en": service_id.replace("_", " ").title()},
            "fee": {"amount": 50.0},
            "processing_days": 7,
            "required_fields": [
                {"field": "full_name", "label_en": "Full Name", "required": True, "type": "text"},
                {"field": "district", "label_en": "District", "required": True, "type": "text"}
            ],
            "required_document_groups": {
                "identity": {"selection_rule": "ANY_ONE", "documents": ["aadhaar_card"]}
            }
        }
