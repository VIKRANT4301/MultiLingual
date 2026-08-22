import pytest
from backend.app.services.dependency_engine import DependencyEngine
from backend.app.models.models import ApplicationState

def test_dependency_check_ncl_missing():
    state_data = {
        "service_id": "ncl_certificate",
        "documents_uploaded": {},
        "completed_certificates": []
    }
    result = DependencyEngine.check_dependencies("ncl_certificate", state_data, None)
    assert result.satisfied is False
    assert "caste_certificate" in result.missing_prerequisites

def test_dependency_check_ncl_satisfied():
    state_data = {
        "service_id": "ncl_certificate",
        "documents_uploaded": {"caste_proof": "VALIDATED"},
        "completed_certificates": ["caste_certificate"]
    }
    result = DependencyEngine.check_dependencies("ncl_certificate", state_data, None)
    assert result.satisfied is True
    assert len(result.missing_prerequisites) == 0

def test_pause_and_resume_flow():
    # Mock ApplicationState
    class DummyAppState:
        def __init__(self):
            self.application_id = 101
            self.current_state = "SERVICE_SELECTION"
            self.state_data = {
                "service_id": "ncl_certificate",
                "full_name": "Krunal Wandhare",
                "annual_income": 450000.0
            }

    class DummyDB:
        def commit(self): pass

    app_state = DummyAppState()
    db = DummyDB()

    # Step 1: Pause application due to missing caste_certificate
    paused_info = DependencyEngine.pause_application(app_state, "caste_certificate", db)
    assert app_state.current_state == "PREREQUISITE_REDIRECT"
    assert app_state.state_data["is_paused"] is True
    assert app_state.state_data["active_dependency"] == "caste_certificate"
    assert app_state.state_data["paused_application"]["preserved_data"]["full_name"] == "Krunal Wandhare"

    # Step 2: Resume application after completing caste_certificate
    resumed_data = DependencyEngine.resume_parent_application(app_state, "caste_certificate", db)
    assert app_state.current_state == "DOCUMENT_COLLECTION"
    assert app_state.state_data["is_paused"] is False
    assert "caste_certificate" in app_state.state_data["completed_certificates"]
    assert app_state.state_data["full_name"] == "Krunal Wandhare"
