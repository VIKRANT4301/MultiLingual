import pytest
from backend.app.services.service_loader import ServiceLoader

def test_load_ncl_service_yaml():
    service_data = ServiceLoader.load_service("ncl_certificate")
    assert service_data is not None
    assert service_data["id"] == "ncl_certificate"
    assert service_data["fee"]["amount"] == 50.0

def test_get_required_fields_ncl():
    fields = ServiceLoader.get_required_fields("ncl_certificate")
    field_names = [f["field"] for f in fields]
    assert "full_name" in field_names
    assert "annual_income" in field_names
    assert "caste_category" in field_names

def test_get_required_documents_ncl():
    doc_groups = ServiceLoader.get_required_documents("ncl_certificate")
    assert "identity" in doc_groups
    assert "caste_proof" in doc_groups

def test_check_eligibility_ncl_eligible():
    state_data = {"annual_income": 450000.0}
    is_eligible, msg = ServiceLoader.check_eligibility("ncl_certificate", state_data)
    assert is_eligible is True
    assert msg is None

def test_check_eligibility_ncl_ineligible():
    state_data = {"annual_income": 950000.0}
    is_eligible, msg = ServiceLoader.check_eligibility("ncl_certificate", state_data)
    assert is_eligible is False
    assert "exceeds" in msg or "आय" in msg or "उत्पन्न" in msg

def test_get_dependency_rules_ncl():
    deps = ServiceLoader.get_dependency_rules("ncl_certificate")
    assert len(deps) > 0
    assert deps[0]["certificate"] == "caste_certificate"
