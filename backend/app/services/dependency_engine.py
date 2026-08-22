import copy
import logging
from typing import Dict, Any, List, Tuple, Optional
from sqlalchemy.orm import Session
from sqlalchemy.orm.attributes import flag_modified
from backend.app.models.models import Application, ApplicationState, Document
from backend.app.services.service_loader import ServiceLoader

logger = logging.getLogger(__name__)

class DependencyCheckResult:
    def __init__(self, satisfied: bool, missing_prerequisites: List[str] = None, error_messages: List[str] = None):
        self.satisfied = satisfied
        self.missing_prerequisites = missing_prerequisites or []
        self.error_messages = error_messages or []

class DependencyEngine:
    """
    Manages prerequisite certificate dependencies.
    Implements Pause → Nested Application Creation → Resume Workflow.
    """

    @staticmethod
    def check_dependencies(service_id: str, state_data: Dict[str, Any], db: Session) -> DependencyCheckResult:
        """
        Checks whether all prerequisite certificates required by service_id are satisfied.
        """
        dep_rules = ServiceLoader.get_dependency_rules(service_id)
        if not dep_rules:
            return DependencyCheckResult(satisfied=True)

        missing = []
        errors = []

        completed_certs = state_data.get("completed_certificates", [])
        docs_uploaded = state_data.get("documents_uploaded", {})

        for rule in dep_rules:
            required_cert = rule.get("certificate")
            if not required_cert:
                continue

            # Check 1: Explicitly uploaded or completed in current session
            is_completed = (
                required_cert in completed_certs or
                f"{required_cert}_proof" in docs_uploaded or
                "caste_proof" in docs_uploaded
            )

            # Check 2: Check database for any COMPLETED application of this cert type for citizen
            citizen_id = state_data.get("citizen_id")
            if not is_completed and citizen_id and db:
                existing = db.query(Application).filter(
                    Application.citizen_id == citizen_id,
                    Application.service_id == required_cert,
                    Application.status == "APPROVED"
                ).first()
                if existing:
                    is_completed = True

            if not is_completed:
                missing.append(required_cert)
                err_msg = rule.get("error_message", {})
                if isinstance(err_msg, dict):
                    msg = err_msg.get(state_data.get("language", "en"), err_msg.get("en", f"{required_cert} is required."))
                else:
                    msg = str(err_msg)
                errors.append(msg)

        if missing:
            return DependencyCheckResult(satisfied=False, missing_prerequisites=missing, error_messages=errors)

        return DependencyCheckResult(satisfied=True)

    @staticmethod
    def pause_application(app_state: ApplicationState, missing_cert: str, db: Session) -> Dict[str, Any]:
        """
        Pauses current application state, preserving all collected citizen data.
        """
        state_data = dict(app_state.state_data or {})
        current_service = state_data.get("service_id", "ncl_certificate")
        current_state = app_state.current_state

        paused_info = {
            "service_id": current_service,
            "state": current_state,
            "missing_prerequisite": missing_cert,
            "preserved_data": copy.deepcopy(state_data)
        }

        state_data["paused_application"] = paused_info
        state_data["is_paused"] = True
        state_data["active_dependency"] = missing_cert

        app_state.state_data = state_data
        app_state.current_state = "PREREQUISITE_REDIRECT"
        if hasattr(app_state, "_sa_instance_state"):
            flag_modified(app_state, "state_data")
        if db:
            db.commit()

        logger.info(f"Application {app_state.application_id} ({current_service}) paused due to missing {missing_cert}")
        return paused_info

    @staticmethod
    def resume_parent_application(parent_app_state: ApplicationState, completed_cert_id: str, db: Session) -> Dict[str, Any]:
        """
        Resumes parent application after child dependency application is completed.
        """
        state_data = dict(parent_app_state.state_data or {})
        paused_info = state_data.get("paused_application", {})
        preserved_data = paused_info.get("preserved_data", {})

        # Restore preserved data
        for k, v in preserved_data.items():
            if k not in ["paused_application", "is_paused", "active_dependency"]:
                state_data[k] = v

        # Add completed cert to completed_certificates list
        completed_certs = state_data.get("completed_certificates", [])
        if completed_cert_id not in completed_certs:
            completed_certs.append(completed_cert_id)
        state_data["completed_certificates"] = completed_certs

        # Mark Caste Proof / Prerequisite as VALIDATED in documents_uploaded
        docs_uploaded = state_data.get("documents_uploaded", {})
        docs_uploaded["caste_proof"] = "VALIDATED"
        state_data["documents_uploaded"] = docs_uploaded

        # Clear pause flags
        state_data["is_paused"] = False
        state_data["active_dependency"] = None
        state_data.pop("paused_application", None)

        parent_app_state.state_data = state_data
        parent_app_state.current_state = "DOCUMENT_COLLECTION"
        if hasattr(parent_app_state, "_sa_instance_state"):
            flag_modified(parent_app_state, "state_data")
        if db:
            db.commit()

        logger.info(f"Resumed parent application {parent_app_state.application_id} after completing {completed_cert_id}")
        return state_data
