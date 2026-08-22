import os
import re
import json
import logging
import datetime
import random
import httpx
from typing import Dict, Any, List, Tuple, Optional
from sqlalchemy.orm import Session
from backend.app.services.data_classification import DataClassificationService
from backend.app.services.policy_engine import OPAPolicyEngine
from backend.app.core.config import settings

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
        raise NotImplementedError

class LocalLLMProvider(LLMProvider):
    # Standard Indian districts for matching
    DISTRICTS = ["nagpur", "mumbai", "pune", "thane", "nashik", "aurangabad", "amravati", "kolhapur", "solapur", "delhi", "patna", "indore"]

    def _detect_language(self, text: str) -> str:
        text_lower = text.lower()
        
        # Marathi keyword hints
        mr_hints = ["मला", "दाखला", "उत्पन्न", "हवा", "पाहिजे", "नाव", "आहे", "होय", "नाही", "माझ्या", "अर्जाची", "स्थिती", "पायजे", "दाखला"]
        # Hindi keyword hints
        hi_hints = ["नमस्ते", "आय", "प्रमाण", "चाहिए", "नाम", "है", "हाँ", "नहीं", "मेरा", "आवेदन", "स्थिति", "चाहिये", "एनसीएल"]
        
        mr_matches = sum(1 for hint in mr_hints if hint in text_lower)
        hi_matches = sum(1 for hint in hi_hints if hint in text_lower)
        
        if mr_matches > hi_matches and mr_matches > 0:
            return "mr"
        elif hi_matches > mr_matches and hi_matches > 0:
            return "hi"
        return "en" # fallback

    def _detect_intent(self, text: str) -> Optional[str]:
        text_lower = text.lower()
        
        # Status checks
        status_words = ["status", "track", "स्थिती", "स्थिति", "चेक", "check status", "अर्जाची"]
        if any(w in text_lower for w in status_words):
            return "STATUS_CHECK"
            
        # Correction
        correction_words = ["correct", "change", "wrong", "बदला", "दुरुस्त", "चुकीचा", "दुरुस्ती", "सुधार"]
        if any(w in text_lower for w in correction_words):
            return "CORRECTION"
            
        # Escalation
        escalate_words = ["officer", "human", "escalate", "अधिकारी", "बोलणे", "तक्रार"]
        if any(w in text_lower for w in escalate_words):
            return "ESCALATE"

        # OBC NCL Certificate
        ncl_words = ["ncl", "non creamy", "नॉन", "क्रीमी", "लेयर"]
        if any(w in text_lower for w in ncl_words):
            return "OBC_NCL_CERTIFICATE"

        # Income Certificate
        income_words = ["income", "उत्पन्न", "आय", "दाखला", "प्रमाण पत्र", "प्रमाणपत्र"]
        if any(w in text_lower for w in income_words):
            return "INCOME_CERTIFICATE"

        return None

    def _extract_entities(self, text: str, state: str, collected_data: Dict[str, Any] = None) -> Dict[str, Any]:
        entities = {}
        text_lower = text.lower()

        # 1. Extract income
        numbers = re.findall(r"\b\d{5,7}\b", text)
        if numbers:
            entities["annual_income"] = float(numbers[0])
        elif "lakh" in text_lower or "लाख" in text_lower:
            lakh_match = re.search(r"(\d+(?:\.\d+)?)\s*(?:lakh|लाख)", text_lower)
            if lakh_match:
                entities["annual_income"] = float(lakh_match.group(1)) * 100000

        # 2. Extract Aadhaar (12 digits)
        aadhaar_match = re.search(r"\b(\d{4}[ \-]?\d{4}[ \-]?\d{4})\b", text)
        if aadhaar_match:
            entities["aadhaar"] = aadhaar_match.group(1).replace(" ", "").replace("-", "")

        # 3. Extract OTP (6 digits)
        otp_match = re.search(r"\b(\d{6})\b", text)
        if otp_match:
            entities["otp"] = otp_match.group(1)

        # 4. Extract consent (yes/no)
        yes_words = ["yes", "yse", "ys", "ye", "yep", "yup", "sure", "agree", "ho", "hoy", "हो", "होय", "haan", "ha", "हाँ", "हा", "स्टार्ट", "सुरू", "सहमत", "मंजूर", "जी", "सहमती"]
        no_words = ["no", "nope", "deny", "disagree", "nahi", "nah", "नाही", "नहीं", "ना"]
        
        # Clean punctuation to match words cleanly
        cleaned_text = re.sub(r"[.,\/#!$%\^&\*;:{}=\-_`~()?।]", " ", text_lower)
        words = cleaned_text.split()
        
        # Check yes/no
        if any(w in words for w in yes_words):
            entities["consent"] = True
            entities["confirm_prerequisite"] = True
            entities["confirm_dob"] = True
        elif any(w in words for w in no_words):
            entities["consent"] = False
            entities["confirm_prerequisite"] = False
            entities["confirm_dob"] = False

        # 5. Extract District
        for district in self.DISTRICTS:
            if district in text_lower:
                entities["district"] = district.capitalize()
                break

        # 6. Extract Name
        if state == "INFORMATION_COLLECTION":
            name_match = re.search(r"(?:my name is|i am|नाव आहे|नाव|नाम|नाम है)\s+([a-zA-Z\s]{3,30})", text, re.IGNORECASE)
            if name_match:
                entities["full_name"] = name_match.group(1).strip()
            elif collected_data and collected_data.get("full_name"):
                # If name already collected, do not overwrite it with fallback district words
                pass
            elif len(text.split()) <= 4 and not any(char.isdigit() for char in text) and "income" not in text_lower and "district" not in text_lower and "ncl" not in text_lower:
                entities["full_name"] = text.strip()

        # 7. Check if user states they lack income proof (Self-Recovering loop trigger)
        lack_proof_keywords = ["no income", "not available", "nahi hai", "nahiye", "available nahi", "नाही", "नाहीये", "आय प्रमाण पत्र नहीं है", "उत्पन्नाचा दाखला नाही"]
        if any(kw in text_lower for kw in lack_proof_keywords) and "income" in text_lower:
            entities["lacks_income_proof"] = True

        # 8. Check for DOB mismatch correction resolution
        dob_match = re.search(r"\b(\d{2}[ \-\/]?\d{2}[ \-\/]?\d{4})\b", text)
        if dob_match:
            entities["dob_resolution"] = dob_match.group(1).replace("/", "-")

        # Set intent in entities
        entities["intent"] = self._detect_intent(text)

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
        
        detected_lang = self._detect_language(text)
        lang = preferred_language if preferred_language in ["en", "hi", "mr"] else detected_lang
        
        intent = self._detect_intent(text)
        entities = self._extract_entities(text, current_state, collected_data)
        
        # Override language if explicitly mentioned
        text_lower = text.lower()
        if "marathi" in text_lower or "मराठी" in text_lower:
            lang = "mr"
        elif "hindi" in text_lower or "हिंदी" in text_lower:
            lang = "hi"
        elif "english" in text_lower or "इंग्रजी" in text_lower:
            lang = "en"

        loc = LOCALES.get(lang, LOCALES.get("en", {}))
        response_text = ""
        
        if intent == "STATUS_CHECK":
            app_no_match = re.search(r"\b(?:NCL|INC)-\d{4}-\d+\b", text, re.IGNORECASE)
            app_no = app_no_match.group(0).upper() if app_no_match else collected_data.get("application_no", "NCL-2026-1026")
            status = collected_data.get("application_status", "Under Verification")
            response_text = loc.get("status_check", "").format(app_no=app_no, status=status)
            
        elif intent == "CORRECTION":
            response_text = loc.get("correction_prompt", "")
            
        elif intent == "ESCALATE":
            case_id = f"ESC-{datetime.datetime.now().strftime('%M%S')}"
            response_text = loc.get("escalated", "").format(case_id=case_id)
            
        else:
            # Standard state responses
            if current_state == "START":
                response_text = loc.get("greet", "")
            elif current_state == "LANGUAGE_SELECTION":
                response_text = loc.get("greet", "")
            elif current_state == "SERVICE_SELECTION":
                if intent == "OBC_NCL_CERTIFICATE":
                    response_text = loc.get("welcome_ncl", "")
                elif intent == "INCOME_CERTIFICATE":
                    response_text = loc.get("welcome_income", "")
                else:
                    response_text = loc.get("greet", "")
            elif current_state == "CONSENT":
                response_text = loc.get("ask_consent", "")
            elif current_state == "INFORMATION_COLLECTION":
                # Check what fields are missing
                name = collected_data.get("full_name") or entities.get("full_name")
                district = collected_data.get("district") or entities.get("district")
                income = collected_data.get("annual_income") or entities.get("annual_income")
                
                if not name:
                    response_text = loc.get("welcome_ncl" if collected_data.get("service_id") == "obc_ncl_certificate" else "welcome_income", "")
                elif not district:
                    response_text = loc.get("ask_district", "")
                elif income is None and collected_data.get("service_id") == "obc_ncl_certificate":
                    response_text = loc.get("ask_income", "")
                else:
                    response_text = loc.get("ask_consent", "")
            elif current_state in ["DOCUMENT_COLLECTION", "DOCUMENT_VALIDATION"]:
                validation_errors = collected_data.get("document_validation_errors", {})
                if validation_errors:
                    err_details = "\n".join([f"- {doc.replace('_', ' ').title()}: {err}" for doc, err in validation_errors.items()])
                    response_text = loc.get("ask_documents_mismatch", "").format(mismatch_details=err_details)
                else:
                    response_text = loc.get("ask_documents", "")
            elif current_state == "PREREQUISITE_PROMPT":
                response_text = loc.get("prerequisite_prompt", "")
            elif current_state == "PREREQUISITE_REDIRECT":
                response_text = loc.get("prerequisite_redirect", "")
            elif current_state == "NESTED_INCOME_FLOW":
                # Responding in prerequisite loop success
                app_no = f"INC-2026-{random.randint(1000,9999)}"
                response_text = loc.get("prerequisite_completed", "").format(app_no=app_no)
            elif current_state == "DOB_MISMATCH_PROMPT":
                response_text = loc.get("dob_mismatch_prompt", "")
            elif current_state == "AUTHENTICATION":
                response_text = loc.get("ask_auth", "")
            elif current_state == "FEE_CALCULATION" or current_state == "PAYMENT":
                response_text = loc.get("ask_payment", "")
            elif current_state == "SUBMISSION":
                app_no = collected_data.get("application_no", "NCL-2026-1026")
                response_text = loc.get("application_submitted", "").format(app_no=app_no)
            elif current_state == "CERTIFICATE_GENERATION":
                response_text = loc.get("ncl_completed" if collected_data.get("service_id") == "obc_ncl_certificate" else "certificate_ready", "")
            else:
                response_text = loc.get("general_error", "")

        return {
            "text": response_text,
            "language": lang,
            "intent": intent or "OBC_NCL_CERTIFICATE",
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
        
        # 1. Run Data classification and OPA evaluation before dispatching to Cloud LLM
        payload_to_evaluate = f"Input: {text} | Context: {json.dumps(collected_data)}"
        opa_decision = OPAPolicyEngine.evaluate_policy(
            payload_to_evaluate, collected_data, db=db, session_id=session_id
        )

        if not opa_decision["allow"]:
            # BLOCKED by OPA! Fallback to Local LLM
            logger.warning(f"[OPA Block] Cloud LLM request denied: {', '.join(opa_decision['reasons'])}. Falling back to local.")
            local_res = await self.local_fallback.process_message(
                text, current_state, collected_data, preferred_language, db, session_id
            )
            local_res["is_blocked"] = True
            local_res["block_reason"] = f"OPA Block: {'; '.join(opa_decision['reasons'])}"
            return local_res

        # 2. Determine Cloud API Config
        provider = settings.LLM_PROVIDER
        if provider == "groq":
            url = "https://api.groq.com/openai/v1/chat/completions"
            api_key = settings.GROQ_API_KEY
            model = settings.GROQ_MODEL
            headers = {
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json"
            }
        elif provider == "openrouter":
            url = "https://openrouter.ai/api/v1/chat/completions"
            api_key = settings.OPENROUTER_API_KEY
            model = settings.OPENROUTER_MODEL
            headers = {
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
                "HTTP-Referer": "http://localhost:8000",
                "X-Title": "Maha Revenue Services Platform"
            }
        else:
            # Fallback to local if no valid provider configured
            return await self.local_fallback.process_message(
                text, current_state, collected_data, preferred_language, db, session_id
            )

        if not api_key:
            # Transparent local fallback if API key is missing
            logger.warning(f"Cloud provider {provider} selected but API key is missing. Falling back to local.")
            return await self.local_fallback.process_message(
                text, current_state, collected_data, preferred_language, db, session_id
            )

        # 3. Construct System Instructions
        system_prompt = f"""You are the conversational AI agent for the Maharashtra Department of Revenue's Maha-Revenue Services Platform.
The department delivers more than 25 certificate services (including income, domicile, caste, solvency, nativity, obc_ncl, ews, residence, legal_heir, etc.).
Your job is to guide users through the workflow, identify their service intent, and extract relevant entities.

Current state machine state: {current_state}
Current collected session data: {json.dumps(collected_data)}
User's preferred language hint: {preferred_language} (Respond in English, Hindi, or Marathi based on user language).

You MUST respond with a single JSON object. The response format is:
{{
  "text": "The conversational reply to the user in their preferred language (English, Hindi, or Marathi)",
  "language": "en | hi | mr",
  "intent": "INCOME_CERTIFICATE | OBC_NCL_CERTIFICATE | etc. (null if unknown)",
  "entities": {{
    "full_name": "extracted citizen name, if mentioned, else null",
    "annual_income": extracted income as float, if mentioned, else null,
    "district": "extracted district name, if mentioned, else null",
    "consent": true/false if consent is given/declined, else null,
    "confirm_prerequisite": true/false if starting prerequisite flow, else null,
    "dob_resolution": "extracted DOB correction, if matching format, else null",
    "otp": "extracted 6 digit OTP, if mentioned, else null",
    "aadhaar": "extracted 12 digit Aadhaar, if mentioned, else null"
  }}
}}
Ensure the JSON is well-formed. Do not add any markdown block wrapper like ```json around it, output only the raw JSON string."""

        # 4. Make external completion call
        payload = {
            "model": model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": text}
            ],
            "temperature": 0.1
        }
        
        if provider == "groq" or "llama-3" in model or "gemma" in model:
            payload["response_format"] = {"type": "json_object"}

        try:
            logger.info(f"Dispatching request to {provider} ({model})...")
            async with httpx.AsyncClient() as client:
                response = await client.post(url, headers=headers, json=payload, timeout=20.0)
                
            if response.status_code == 200:
                res_data = response.json()
                content_str = res_data["choices"][0]["message"]["content"].strip()
                
                # Strip markdown codeblocks if LLM returned them
                if content_str.startswith("```"):
                    content_str = re.sub(r"^```(?:json)?\n|\n```$", "", content_str, flags=re.MULTILINE)
                    
                parsed = json.loads(content_str)
                logger.info(f"Successfully processed Cloud response from {provider}.")
                parsed["is_blocked"] = False
                parsed["block_reason"] = None
                return parsed
            else:
                logger.error(f"{provider} returned error status {response.status_code}: {response.text}")
                # Fallback to local
                fallback_res = await self.local_fallback.process_message(
                    text, current_state, collected_data, preferred_language, db, session_id
                )
                fallback_res["text"] = f"[{provider.capitalize()} API Error - Local Fallback] " + fallback_res["text"]
                return fallback_res

        except Exception as e:
            logger.error(f"Cloud LLM request to {provider} failed: {e}. Falling back to local.")
            fallback_res = await self.local_fallback.process_message(
                text, current_state, collected_data, preferred_language, db, session_id
            )
            fallback_res["text"] = f"[{provider.capitalize()} Exception - Local Fallback] " + fallback_res["text"]
            return fallback_res
