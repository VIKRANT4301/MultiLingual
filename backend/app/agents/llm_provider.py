import os
import re
import json
import logging
from typing import Dict, Any, List, Tuple, Optional
from sqlalchemy.orm import Session
from backend.app.services.data_classification import DataClassificationService

logger = logging.getLogger(__name__)

# Load translations
LOCALES = {}
try:
    locales_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))), "data", "locales")
    for lang in ["en", "hi", "mr"]:
        file_path = os.path.join(locales_dir, f"{lang}.json")
        if os.path.exists(file_path):
            with open(file_path, "r", encoding="utf-8") as f:
                LOCALES[lang] = json.load(f)
        else:
            # Fallback inline translations if file not found during tests
            LOCALES[lang] = {}
except Exception as e:
    logger.error(f"Error loading locales: {e}")

class LLMProvider:
    async def process_message(
        self, 
        text: str, 
        current_state: str, 
        collected_data: Dict[str, Any], 
        preferred_language: str = "en",
        db: Session = None,
        session_id: str = None
    ) -> Dict[str, Any]:
        """
        Processes message and returns a dict with:
        - text: response text
        - language: detected or preferred language
        - intent: detected intent (e.g. INCOME_CERTIFICATE)
        - entities: dict of extracted entities
        - is_blocked: boolean (data guard blocked)
        """
        raise NotImplementedError

class LocalLLMProvider(LLMProvider):
    # Standard Indian districts for matching
    DISTRICTS = ["nagpur", "mumbai", "pune", "thane", "nashik", "aurangabad", "nagpur", "amravati", "kolhapur", "solapur", "delhi", "patna", "indore"]

    def _detect_language(self, text: str) -> str:
        text_lower = text.lower()
        
        # Marathi keyword hints
        mr_hints = ["मला", "दाखला", "उत्पन्न", "हवा", "पाहिजे", "नाव", "आहे", "होय", "नाही", "माझ्या", "अर्जाची", "स्थिती"]
        # Hindi keyword hints
        hi_hints = ["नमस्ते", "आय", "प्रमाण", "चाहिए", "नाम", "है", "हाँ", "नहीं", "मेरा", "आवेदन", "स्थिति"]
        
        mr_matches = sum(1 for hint in mr_hints if hint in text_lower)
        hi_matches = sum(1 for hint in hi_hints if hint in text_lower)
        
        if mr_matches > hi_matches and mr_matches > 0:
            return "mr"
        elif hi_matches > mr_matches and hi_matches > 0:
            return "hi"
        return "en" # fallback

    def _detect_intent(self, text: str) -> Optional[str]:
        text_lower = text.lower()
        
        # Check for status checks
        status_words = ["status", "track", "स्थिती", "स्थिति", "चेक", "check status", "अर्जाची"]
        if any(w in text_lower for w in status_words):
            return "STATUS_CHECK"
            
        # Check for correction
        correction_words = ["correct", "change", "wrong", "बदला", "दुरुस्त", "चुकीचा", "दुरुस्ती", "सुधार"]
        if any(w in text_lower for w in correction_words):
            return "CORRECTION"
            
        # Check for escalation
        escalate_words = ["officer", "human", "escalate", "अधिकारी", "बोलणे", "तक्रार"]
        if any(w in text_lower for w in escalate_words):
            return "ESCALATE"

        # Check for Income Certificate
        income_words = ["income", "उत्पन्न", "आय", "दाखला", "प्रमाण पत्र", "प्रमाणपत्र"]
        if any(w in text_lower for w in income_words):
            return "INCOME_CERTIFICATE"

        return None

    def _extract_entities(self, text: str, state: str) -> Dict[str, Any]:
        entities = {}
        text_lower = text.lower()

        # 1. Extract income (numbers representing income, e.g. 500000, 1.2 lakhs, etc.)
        # Look for numbers between 10,000 and 10,000,000
        numbers = re.findall(r"\b\d{5,7}\b", text)
        if numbers:
            entities["annual_income"] = float(numbers[0])
        elif "lakh" in text_lower or "लाख" in text_lower:
            # Parse things like "1.5 lakh" or "१.५ लाख"
            lakh_match = re.search(r"(\d+(?:\.\d+)?)\s*(?:lakh|लाख)", text_lower)
            if lakh_match:
                entities["annual_income"] = float(lakh_match.group(1)) * 100000

        # 2. Extract Aadhaar (12 digits)
        aadhaar_match = re.search(r"\b(\d{4}[ \-]?\d{4}[ \-]?\d{4})\b", text)
        if aadhaar_match:
            # Clean spaces/dashes
            entities["aadhaar"] = aadhaar_match.group(1).replace(" ", "").replace("-", "")

        # 3. Extract OTP (6 digits)
        otp_match = re.search(r"\b(\d{6})\b", text)
        if otp_match:
            entities["otp"] = otp_match.group(1)

        # 4. Extract consent (yes/no)
        yes_words = ["yes", "yup", "sure", "agree", "ho", "hoy", "हो", "होय", "haan", "ha", "हाँ", "हा"]
        no_words = ["no", "nope", "deny", "disagree", "nahi", "nah", "नाही", "नहीं", "ना"]
        
        # exact/word boundary matching for consent
        words = text_lower.split()
        if any(w in words for w in yes_words):
            entities["consent"] = True
        elif any(w in words for w in no_words):
            entities["consent"] = False

        # 5. Extract District
        for district in self.DISTRICTS:
            if district in text_lower:
                entities["district"] = district.capitalize()
                break

        # 6. Extract Name
        # If the state is welcoming name input, try to grab the whole name
        if state == "LANGUAGE_SELECTION" or state == "SERVICE_SELECTION":
            # Just starting out
            pass
        elif state == "INFORMATION_COLLECTION":
            # If name is not yet collected, parse name
            name_match = re.search(r"(?:my name is|i am|नाव आहे|नाव|नाम|नाम है)\s+([a-zA-Z\s]{3,30})", text, re.IGNORECASE)
            if name_match:
                entities["full_name"] = name_match.group(1).strip()
            elif len(text.split()) <= 4 and not any(char.isdigit() for char in text) and "income" not in text_lower and "district" not in text_lower:
                # If they just entered their name directly (e.g. "Vikram Patil" or "विक्रम पाटील")
                entities["full_name"] = text.strip()

        return entities

    async def process_message(
        self, 
        text: str, 
        current_state: str, 
        collected_data: Dict[str, Any], 
        preferred_language: str = "en",
        db: Session = None,
        session_id: str = None
    ) -> Dict[str, Any]:
        
        # 1. Detect language & intent
        detected_lang = self._detect_language(text)
        # Use preferred language if it was selected in the UI, else use detected
        lang = preferred_language if preferred_language in ["en", "hi", "mr"] else detected_lang
        
        intent = self._detect_intent(text)
        entities = self._extract_entities(text, current_state)
        
        # Get localized dict
        loc = LOCALES.get(lang, LOCALES.get("en", {}))

        # Check if the user is asking to switch languages explicitly
        text_lower = text.lower()
        if "marathi" in text_lower or "मराठी" in text_lower:
            lang = "mr"
            loc = LOCALES["mr"]
        elif "hindi" in text_lower or "हिंदी" in text_lower:
            lang = "hi"
            loc = LOCALES["hi"]
        elif "english" in text_lower or "इंग्रजी" in text_lower:
            lang = "en"
            loc = LOCALES["en"]

        # Formulate response based on State Machine
        response_text = ""
        
        if intent == "STATUS_CHECK":
            # Try to find application number in text (e.g., INC-2026-000123)
            app_no_match = re.search(r"\bINC-\d{4}-\d+\b", text, re.IGNORECASE)
            app_no = app_no_match.group(0).upper() if app_no_match else collected_data.get("application_no", "INC-2026-001005")
            # We will handle the database lookup in the orchestrator, but provide a template response here
            status = collected_data.get("application_status", "SUBMITTED")
            response_text = loc.get("status_check", "").format(app_no=app_no, status=status)
            
        elif intent == "CORRECTION":
            response_text = loc.get("correction_prompt", "")
            
        elif intent == "ESCALATE":
            case_id = f"ESC-{datetime.datetime.now().strftime('%M%S')}"
            response_text = loc.get("escalated", "").format(case_id=case_id)
            
        else:
            # Standard State transitions handled locally
            if current_state == "START":
                response_text = loc.get("greet", "")
            elif current_state == "LANGUAGE_SELECTION":
                response_text = loc.get("greet", "")
            elif current_state == "SERVICE_SELECTION":
                if intent == "INCOME_CERTIFICATE" or "income" in text_lower or "उत्पन्न" in text_lower or "आय" in text_lower:
                    response_text = loc.get("welcome_income", "")
                else:
                    response_text = loc.get("greet", "")
            elif current_state == "CONSENT":
                response_text = loc.get("ask_consent", "")
            elif current_state == "INFORMATION_COLLECTION":
                # Check what fields are missing
                name = collected_data.get("full_name") or entities.get("full_name")
                income = collected_data.get("annual_income") or entities.get("annual_income")
                district = collected_data.get("district") or entities.get("district")
                
                if not name:
                    response_text = loc.get("welcome_income", "")
                elif not income:
                    response_text = loc.get("ask_income", "")
                elif not district:
                    response_text = loc.get("ask_district", "")
                else:
                    response_text = loc.get("ask_consent", "")
            elif current_state == "CONSENT_REQUESTED":
                response_text = loc.get("ask_consent", "")
            elif current_state == "DOCUMENT_COLLECTION":
                response_text = loc.get("ask_documents", "")
            elif current_state == "AUTHENTICATION":
                response_text = loc.get("ask_auth", "")
            elif current_state == "FEE_CALCULATION" or current_state == "PAYMENT":
                response_text = loc.get("ask_payment", "")
            elif current_state == "SUBMISSION":
                app_no = collected_data.get("application_no", "INC-2026-000000")
                response_text = loc.get("application_submitted", "").format(app_no=app_no)
            elif current_state == "CERTIFICATE_GENERATION":
                response_text = loc.get("certificate_ready", "")
            else:
                response_text = loc.get("general_error", "")

        return {
            "text": response_text,
            "language": lang,
            "intent": intent or "INCOME_CERTIFICATE",
            "entities": entities,
            "is_blocked": False,
            "block_reason": None
        }

class CloudLLMProvider(LLMProvider):
    def __init__(self):
        self.local_fallback = LocalLLMProvider()

    async def process_message(
        self, 
        text: str, 
        current_state: str, 
        collected_data: Dict[str, Any], 
        preferred_language: str = "en",
        db: Session = None,
        session_id: str = None
    ) -> Dict[str, Any]:
        
        # 1. Run Data classification check before dispatching to Cloud LLM API
        # Combine user text and collected data to evaluate policy
        payload_to_evaluate = f"Input: {text} | Context: {json.dumps(collected_data)}"
        is_allowed, classification = DataClassificationService.evaluate_external_policy(
            payload_to_evaluate, provider="cloud_llm", db=db, conversation_id=session_id
        )

        if not is_allowed:
            # BLOCKED! Fallback to Local LLM immediately
            logger.warning(f"Cloud LLM dispatch blocked by data guard due to {classification} information. Falling back to local.")
            local_res = await self.local_fallback.process_message(
                text, current_state, collected_data, preferred_language, db, session_id
            )
            local_res["is_blocked"] = True
            local_res["block_reason"] = f"Cloud LLM call blocked: RESTRICTED/SENSITIVE ({classification}) data detected."
            return local_res

        # If allowed, check if cloud credentials are set, else fallback to local
        cloud_url = settings.CLOUD_LLM_URL
        cloud_key = settings.CLOUD_LLM_API_KEY
        
        if not cloud_url or not cloud_key:
            # No credentials -> Transparent local execution
            return await self.local_fallback.process_message(
                text, current_state, collected_data, preferred_language, db, session_id
            )

        # Implementation for cloud LLM post request (e.g. Gemini, OpenAI, etc.)
        # For the POC, we return a mock Cloud response if variables are set
        try:
            # Dummy cloud API dispatch simulation
            logger.info("Executing external Cloud LLM API request...")
            # We would make an HTTP request to cloud_url with headers {"Authorization": f"Bearer {cloud_key}"}
            # Since this is a POC, we simulate the Cloud provider response based on local rules to be robust
            res = await self.local_fallback.process_message(
                text, current_state, collected_data, preferred_language, db, session_id
            )
            res["text"] = "[Cloud Response] " + res["text"]
            return res
        except Exception as e:
            logger.error(f"Cloud LLM request failed: {e}. Falling back to local.")
            return await self.local_fallback.process_message(
                text, current_state, collected_data, preferred_language, db, session_id
            )
