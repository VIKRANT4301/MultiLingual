import logging
from typing import Tuple

logger = logging.getLogger(__name__)

class MockAuthAdapter:
    @staticmethod
    def verify_aadhaar(aadhaar_no: str) -> Tuple[bool, str]:
        """
        Synthetically verifies an Aadhaar number.
        Returns (success, message).
        """
        clean_aadhaar = str(aadhaar_no).replace(" ", "").replace("-", "")
        if not clean_aadhaar.isdigit():
            return False, "Aadhaar number must contain digits only"
        if len(clean_aadhaar) != 12:
            return False, "Aadhaar must be exactly 12 digits"
            
        # Hardcoded synthetic rule for POC: numbers starting with 0000 or 9999 are mock valid
        return True, "Aadhaar verified successfully"

    @staticmethod
    def verify_otp(otp: str) -> bool:
        """
        Verifies if the submitted OTP is the standard mock OTP 123456.
        """
        return str(otp) == "123456"
