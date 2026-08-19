import os
import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)

class IndicASRAdapter:
    def __init__(self):
        # Local maps of dialect variations to standard transcript phrases
        self.DIALECT_MAP = {
            # Hindi/Hinglish dialect/rural variations
            "mere bete ke college admission ke liye ncl certificate chahiye": "मेरे बेटे के कॉलेज एडमिशन के लिए एनसीएल सर्टिफिकेट चाहिए",
            "ncl certificate chahiye": "एनसीएल सर्टिफिकेट चाहिए",
            "income proof nahi hai": "आय प्रमाण पत्र नहीं है",
            "mere paas income proof nahi hai": "मेरे पास आय प्रमाण पत्र नहीं है",
            "haan, start karo": "हाँ, स्टार्ट करो",
            "ha start karo": "हाँ, स्टार्ट करो",
            "otp is 741286": "741286",
            "double seven triple nine": "77999",

            # Marathi dialect variations (Vidarbha/Marathwada influence)
            "mazya mulachya admission sathi ncl दाखला हवा": "माझ्या मुलाच्या ॲडमिशनसाठी एनसीएल दाखला हवा आहे",
            "ncl dakhla pahije": "एनसीएल दाखला पाहिजे",
            "utpannacha dakhla nahiye": "उत्पन्नाचा दाखला नाहीये",
            "mazyakade utpannacha dakhla nahi aahe": "माझ्याकडे उत्पन्नाचा दाखला नाही आहे",
            "hoy, suru kara": "होय, सुरू करा",
            "ho suru kara": "होय, सुरू करा"
        }

    def transcribe_audio(self, audio_file_path: str, hint_language: str = None) -> Dict[str, Any]:
        """
        Simulates local IndicASR inference. Returns identified language, standard transcription,
        and confidence metrics.
        """
        filename = os.path.basename(audio_file_path).lower()
        logger.info(f"[IndicASR] Analyzing audio file: {filename}")

        # Default transcript
        detected_lang = hint_language or "hi"
        transcript = "मेरे बेटे के कॉलेज एडमिशन के लिए एनसीएल सर्टिफिकेट चाहिए"
        confidence = 0.96

        # Determine transcript by looking at filename patterns (to allow flexible integration tests)
        if "ncl_request" in filename or "ncl" in filename:
            if "mr" in filename or "marathi" in filename:
                detected_lang = "mr"
                transcript = "माझ्या मुलाच्या ॲडमिशनसाठी एनसीएल दाखला हवा आहे"
            else:
                detected_lang = "hi"
                transcript = "मेरे बेटे के कॉलेज एडमिशन के लिए एनसीएल सर्टिफिकेट चाहिए"
        elif "missing_income" in filename or "no_income" in filename:
            if "mr" in filename or "marathi" in filename:
                detected_lang = "mr"
                transcript = "माझ्याकडे उत्पन्नाचा दाखला नाही आहे"
            else:
                detected_lang = "hi"
                transcript = "मेरे पास आय प्रमाण पत्र नहीं है"
        elif "start_income" in filename or "confirm_start" in filename:
            if "mr" in filename or "marathi" in filename:
                detected_lang = "mr"
                transcript = "होय, सुरू करा"
            else:
                detected_lang = "hi"
                transcript = "हाँ, स्टार्ट करो"
        elif "otp" in filename:
            detected_lang = "en"
            transcript = "741286"
        elif "marathi" in filename or "mr" in filename:
            detected_lang = "mr"
            transcript = "माझ्या मुलाच्या ॲडमिशनसाठी एनसीएल दाखला हवा आहे"
        elif "hindi" in filename or "hi" in filename:
            detected_lang = "hi"
            transcript = "मेरे बेटे के कॉलेज एडमिशन के लिए एनसीएल सर्टिफिकेट चाहिए"

        # Check if the filename contains exact text matches for our dialect map (clean up extensions)
        clean_name = os.path.splitext(filename)[0].replace("_", " ").replace("-", " ")
        for key, value in self.DIALECT_MAP.items():
            if key in clean_name:
                transcript = value
                if value.startswith("माझ्या") or value.startswith("उत्पन्न") or value.startswith("होय"):
                    detected_lang = "mr"
                else:
                    detected_lang = "hi"
                break

        return {
            "transcript": transcript,
            "detected_language": detected_lang,
            "confidence": confidence,
            "engine": "IndicASR-v2-CPU"
        }
