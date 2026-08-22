# Logical, Security, and Scalability Architecture

## 1. Logical Architecture

The platform uses a modular layout with clear separation of concerns across channels, state orchestration, NLU reasoning, and validation layers.

```text
 Citizen (Web Portal / WhatsApp / IVR Simulator)
                       │
                       ▼
               Channel Adapters
                       │
                       ▼
               Data Guard (DLP)
         (Sovereignty Policy Evaluator)
                       │
         ┌─────────────┴─────────────┐
         ▼                           ▼
    Local Processing          Cloud NLU (Fallback)
         │                           │
         └─────────────┬─────────────┘
                       ▼
         StateMachineOrchestrator
         (Transient state loops & rules)
                       │
         ┌─────────────┼─────────────┐
         ▼             ▼             ▼
    Form Filling   Mock OCR    Policy Engine
                       │
                       ▼
               Mock Payment Gateway
                       │
                       ▼
             SQLite DB & Audit Log
```

- **Channel Adapters**: Translate channel-specific payloads (Web text, WhatsApp, IVR caller keypad inputs) into a standard conversation context.
- **Data Guard (DLP)**: Evaluates user input against privacy/PII policies. Sensitive fields (like Aadhaar cards, emails, phone numbers) are redacted or intercepted before leaving the local processing boundary.
- **State Machine Orchestrator**: Executes a deterministic state graph (START, LANGUAGE_SELECTION, SERVICE_SELECTION, INFORMATION_COLLECTION, CONSENT, FORM_VALIDATION, DOCUMENT_COLLECTION, DOCUMENT_VALIDATION, AUTHENTICATION, FEE_CALCULATION, PAYMENT, SUBMISSION, COMPLETED) to ensure the citizen's journey follows a structured regulatory workflow.

---

## 2. Security Architecture (PII Protection)

- **PII Masking**: Input strings are scanned using compiled regex boundaries. Restricted items are logged with mask patterns (e.g. `Aadhaar = ********9012`).
- **Sovereignty Interceptor**: Any Cloud LLM execution goes through `OPAPolicyEngine.evaluate_policy`. If Aadhaar, PAN, phone, or email is detected in the outgoing context, evaluated action is forced to `LOCAL_ONLY` to block API transmission.

---

## 3. Scalability Architecture (YAML Configuration)

Adding new certificates is completely configuration-driven. To add a new service:
1. Create a `.yaml` definition in the `services/` directory (e.g. `services/new_certificate.yaml`).
2. Add its localization titles in `hi.json`, `mr.json`, and `en.json`.
3. The platform dynamically loads and seeds the service into the database on startup.
4. The conversational state machine parses its required fields and documents automatically.
