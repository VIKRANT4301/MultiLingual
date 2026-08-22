from backend.app.services.data_classification import DataClassificationService
from backend.app.services.policy_engine import OPAPolicyEngine

def test_data_classification():
    # Public content
    assert DataClassificationService.classify_content("Hello how are you") == "PUBLIC"
    
    # Sensitive content (Aadhaar or PAN)
    assert DataClassificationService.classify_content("My Aadhaar is 1234-5678-9012") == "SENSITIVE"
    assert DataClassificationService.classify_content("My PAN is ABCDE1234F") == "SENSITIVE"
    
    # Restricted content (Phone or Email or Address keywords)
    assert DataClassificationService.classify_content("Reach me at test@example.com") == "RESTRICTED"
    assert DataClassificationService.classify_content("Call me on 9876543210") == "RESTRICTED"

def test_policy_engine_evaluation():
    # Safe message
    res_safe = OPAPolicyEngine.evaluate_policy("I want to apply for Income Certificate", {})
    assert res_safe["allow"] is True
    assert res_safe["action"] == "CLOUD_APPROVED"
    assert len(res_safe["reasons"]) == 0
    
    # Message containing Aadhaar (DLP Block)
    res_block_aadhaar = OPAPolicyEngine.evaluate_policy("My Aadhaar is 1234 5678 9012", {})
    assert res_block_aadhaar["allow"] is False
    assert res_block_aadhaar["action"] == "LOCAL_ONLY"
    assert any("Aadhaar" in r for r in res_block_aadhaar["reasons"])
    
    # Message containing Phone
    res_block_phone = OPAPolicyEngine.evaluate_policy("My phone is 9876543210", {})
    assert res_block_phone["allow"] is False
    assert res_block_phone["action"] == "LOCAL_ONLY"
    assert any("Privacy violation" in r or "mobile" in r.lower() for r in res_block_phone["reasons"])
