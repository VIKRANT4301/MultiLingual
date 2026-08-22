# 🏛️ Multilingual Voice-First Revenue Services Platform
## Enterprise-Level Architecture, System Design & Technology Strategy

> **Based on:** AI Club Hackathon Problem Statement ([`first.md`](file:///d:/AI%20Club%20Hackathon/Document/first.md))
> **Target:** Enterprise-grade, on-premise-ready, data-sovereign, omnichannel certificate services platform for a Government Revenue Department.
> **Scoring weight:** Enterprise Architecture & Data Isolation (4/10) · Feature Completeness (4/10) · Code Quality & Technical Execution (2/10)

---

## Table of Contents

1. [Problem Deep-Dive & Analysis](#1-problem-deep-dive--analysis)
2. [Enterprise Design Principles](#2-enterprise-design-principles)
3. [High-Level System Architecture](#3-high-level-system-architecture)
4. [Full System Flow — End-to-End Journey](#4-full-system-flow--end-to-end-journey)
5. [Component-Level Deep Dive](#5-component-level-deep-dive)
   - 5.1 Channel Layer
   - 5.2 Conversation & Orchestration Engine
   - 5.3 Business & Rules Engine
   - 5.4 Service Adapters
   - 5.5 Data Guard (Trust Boundary)
   - 5.6 Data Layer
   - 5.7 Outcome Engine
   - 5.8 Operational Dashboard
6. [AI & ML Layer — Model-by-Model Breakdown](#6-ai--ml-layer--model-by-model-breakdown)
7. [Complete Technology Stack & Justifications](#7-complete-technology-stack--justifications)
8. [Data Sovereignty & Security Architecture](#8-data-sovereignty--security-architecture)
9. [Conversation State Machine Design](#9-conversation-state-machine-design)
10. [Multi-Language & Multi-Modal Strategy](#10-multi-language--multi-modal-strategy)
11. [Certificate Services Catalogue (25+ Services)](#11-certificate-services-catalogue-25-services)
12. [Document Intelligence Pipeline](#12-document-intelligence-pipeline)
13. [Payment & Authentication Architecture](#13-payment--authentication-architecture)
14. [Observability, Logging & Audit Architecture](#14-observability-logging--audit-architecture)
15. [DevOps, CI/CD & Reproducible Deployment](#15-devops-cicd--reproducible-deployment)
16. [Testing Strategy — Unit, Integration, Adversarial](#16-testing-strategy--unit-integration-adversarial)
17. [Repository Structure & Code Organization](#17-repository-structure--code-organization)
18. [Sequence Diagrams — Key Flows](#18-sequence-diagrams--key-flows)
19. [Synthetic Personas & Test Data Strategy](#19-synthetic-personas--test-data-strategy)
20. [Enterprise-Level Enhancements & Differentiators](#20-enterprise-level-enhancements--differentiators)
21. [Scoring Alignment Matrix](#21-scoring-alignment-matrix)
22. [Implementation Roadmap](#22-implementation-roadmap)
23. [Architecture Decision Records (ADRs)](#23-architecture-decision-records-adrs)

---

## 1. Problem Deep-Dive & Analysis

### 1.1 What the Government Really Needs

The Revenue Department is not just asking for a chatbot. They need a **digital service delivery nervous system** — one that:

- Handles **25+ distinct certificate types** (income, domicile, caste, solvency, nativity, etc.), each with its own validation rules, eligibility criteria, required documents, and fee schedules.
- Serves citizens with **wildly varying literacy levels** — from a highly educated professional to a first-generation smartphone user in a rural area who speaks in dialect-heavy local language.
- Works across **radically different channels simultaneously** — WhatsApp (text + voice notes), IVR (touch-tone phone), web portal, and mobile app — and must **remember context** when a citizen switches channels mid-journey.
- Ensures **zero PII leakage to cloud** for citizen or government data, while still leveraging cloud AI for approved, non-sensitive tasks.
- Provides **real-time operational intelligence** — dashboards, anomaly detection, latency metrics, error rates — not just for the POC demo but as a live running system.

### 1.2 The Five Hard Problems

| # | Hard Problem | Why It's Hard | Our Solution Pillar |
|---|---|---|---|
| 1 | **Omnichannel continuity** | Same citizen may start on WhatsApp and finish on IVR — session state must transfer invisibly | Context Vault (channel-agnostic state machine) |
| 2 | **Local data sovereignty** | Government citizen data cannot leave on-premise boundary, yet AI services are mostly cloud | Data Guard + local LLM/ASR/OCR |
| 3 | **25+ service catalog** | Each certificate has unique rules; implementing each individually doesn't scale | Declarative YAML-driven rules engine |
| 4 | **Varying literacy** | Voice input from illiterate users is noisy, code-mixed, dialectal | Literacy-adaptive dialogue + local ASR |
| 5 | **Audit & compliance** | Every action on sensitive data must be traceable, immutable, and separately logged | Dual-stream audit architecture |

### 1.3 The POC vs. Enterprise Gap — Bridging It

Most POCs fail to demonstrate **trust**. They show a happy path. Enterprise systems must show:

- **Failure recovery** — what happens when the document upload fails? When payment gateway times out? When ASR produces garbage?
- **Adversarial behavior** — what happens when a user deliberately tries to submit wrong data, replay transactions, or bypass validation?
- **Data boundary enforcement** — not as a diagram box, but as a **runtime-enforced gate** that can be demonstrated live by triggering a blocked call.

This document ensures every component is designed to be **demoable under adversarial conditions**, not just in the happy path.

---

## 2. Enterprise Design Principles

### 2.1 Core Architectural Principles

```
┌─────────────────────────────────────────────────────────────────────┐
│                   ENTERPRISE DESIGN PRINCIPLES                       │
├─────────────────────────────────────────────────────────────────────┤
│  1. LOCAL-FIRST INTELLIGENCE    — AI runs on-prem by default         │
│  2. CLOUD-SECOND, GATE-GUARDED  — Cloud is opt-in with enforcement   │
│  3. ADAPTER PATTERN EVERYWHERE  — Mock = Real, swappable via config  │
│  4. DECLARATIVE OVER IMPERATIVE — Config files, not code, add svc    │
│  5. STATE IS CHANNEL-AGNOSTIC   — Session lives in vault, not wire   │
│  6. AUDIT IS A FIRST-CLASS CITIZEN — Separate stream, not log noise  │
│  7. TESTABILITY BY DESIGN       — Every component is unit-testable   │
│  8. OBSERVABILITY FROM DAY ONE  — Metrics/traces/logs from start     │
│  9. FAIL SAFE, NEVER FAIL OPEN  — Default to block, not allow        │
│ 10. LITERACY-ADAPTIVE UX        — Dialect, complexity, channel aware │
└─────────────────────────────────────────────────────────────────────┘
```

### 2.2 Trust Boundary Model

The system operates across **three trust zones**:

| Zone | Label | Data Classification | Allowed Operations |
|---|---|---|---|
| **Zone 0** | On-Premise Core | `RESTRICTED` (citizen PII, government records) | All operations; no outbound to cloud |
| **Zone 1** | Sanitized Proxy | `QUASI-IDENTIFIER` removed, tokenized | Controlled cloud calls via Data Guard |
| **Zone 2** | Cloud Services | `NON-SENSITIVE` only (language polish, fallback ASR with synthetic data) | Stateless calls, no persistence |

### 2.3 API-First Contract Design

Every component boundary is an explicit API contract. No direct function calls across module boundaries. This enables:
- Independent deployment and scaling
- Mock substitution for testing
- Version evolution without cascading changes

---

## 3. High-Level System Architecture

```
╔══════════════════════════════════════════════════════════════════════════════════════════╗
║                   MULTILINGUAL VOICE-FIRST REVENUE SERVICES PLATFORM                    ║
║                              Enterprise Architecture v1.0                                ║
╚══════════════════════════════════════════════════════════════════════════════════════════╝

┌─────────────────────────────────────────────────────────────────────────────────────────┐
│                               CITIZEN TOUCH POINTS                                      │
│   📱 WhatsApp    📞 IVR / PSTN    🌐 Web Portal    📲 Mobile App    🖥️ Kiosk           │
└───────────────────────────────────┬─────────────────────────────────────────────────────┘
                                    │ Raw channel events
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────────────────┐
│                              [CHANNEL LAYER]                                            │
│  │WhatsApp      │  │IVR Adapter   │  │Web Adapter   │  │Mobile Adapter│               │
│  │Adapter       │  │+ Local ASR   │  │(REST/WS)     │  │(REST/Push)   │               │
│  │(Webhook)     │  │(Whisper)     │  │              │  │              │               │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘               │
│         └──────────────────┴──────────────────┴──────────────────┘                     │
│                                    │ ChannelMessage{citizen_ref, modality, payload}      │
│                         [Channel Normalizer + Citizen Resolver]                         │
└───────────────────────────────────┬─────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────────────────┐
│                    [CONVERSATION & ORCHESTRATION ENGINE]                                │
│                                                                                         │
│  ┌──────────────────────────────────────────────────────────────────────────────────┐   │
│  │                         LOCAL NLU PIPELINE                                       │   │
│  │  Local LLM (Llama 3.1 8B/Phi-3) → Intent + Entity Extraction + PII Tagging      │   │
│  │  Language Detector → Literacy Analyzer → Code-Mix Handler                       │   │
│  └──────────────────────────────────────────────────────────────────────────────────┘   │
│                                    │                                                     │
│  ┌──────────────────────────────────────────────────────────────────────────────────┐   │
│  │                    LANGGRAPH STATE MACHINE                                       │   │
│  │                                                                                   │   │
│  │  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐          │   │
│  │  │ INTAKE   │  │VALIDATION│  │DOCUMENT  │  │ PAYMENT  │  │ESCALATION│          │   │
│  │  │  AGENT   │→ │  AGENT   │→ │  AGENT   │→ │  AGENT   │→ │  AGENT   │          │   │
│  │  │(slot fill)│  │(rules)  │  │(vision)  │  │(payment) │  │(RAG+HO)  │          │   │
│  │  └──────────┘  └──────────┘  └──────────┘  └──────────┘  └──────────┘          │   │
│  │                              STATUS AGENT (async)                                │   │
│  └──────────────────────────────────────────────────────────────────────────────────┘   │
│                                    │                                                     │
│  ┌──────────────────────────────────────────────────────────────────────────────────┐   │
│  │                    CONTEXT VAULT (Context Manager)                               │   │
│  │  Redis/PostgreSQL: {citizen_ref → ConversationState} channel-agnostic session   │   │
│  └──────────────────────────────────────────────────────────────────────────────────┘   │
└───────────────────────────────────┬─────────────────────────────────────────────────────┘
                                    │ {intent, entities, slots, next_action}
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────────────────┐
│                         [BUSINESS & RULES ENGINE]                                      │
│                                                                                         │
│  ┌─────────────────────────────────┐   ┌───────────────────────────────────────────┐   │
│  │  Service Catalogue              │   │  Validation Engine                        │   │
│  │  25+ YAML/JSON specs            │   │  Regex + Range + Cross-field rules        │   │
│  │  income.yaml, caste.yaml...     │   │  Eligibility conditions                   │   │
│  └─────────────────────────────────┘   └───────────────────────────────────────────┘   │
│                                                                                         │
│  ┌─────────────────────────────────┐   ┌───────────────────────────────────────────┐   │
│  │  LightGBM Fraud/Anomaly Scorer  │   │  Fee Calculator + Waiver Rules            │   │
│  │  (local, explainable, fast)     │   │  Dynamic fee schedules per service        │   │
│  └─────────────────────────────────┘   └───────────────────────────────────────────┘   │
└───────────────────────────────────┬─────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────────────────┐
│                          [SERVICE ADAPTERS]                                             │
│                                                                                         │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐                │
│  │   AUTH   │  │DOCUMENT  │  │ PAYMENT  │  │NOTIFICATN│  │ESCALATION│                │
│  │ ADAPTER  │  │ ADAPTER  │  │ ADAPTER  │  │ ADAPTER  │  │ ADAPTER  │                │
│  │(OTP/biom)│  │(LocalOCR)│  │(Gateway) │  │(SMS/push)│  │(RAG+HO)  │                │
│  └──────────┘  └──────────┘  └──────────┘  └──────────┘  └──────────┘                │
└───────────┬──────────────────────────────────────────────────────────────────────────  ┘
            │                                         ▲ Outbound cloud call attempt
            │                                         │
            │                              ╔══════════╧══════════╗
            │                              ║   [DATA GUARD]      ║
            │                              ║   OPA/Rego Policy   ║
            │                              ║   Engine            ║
            │                              ║   ┌─────────────┐   ║
            │                              ║   │RESTRICTED?  │   ║
            │                              ║   │→ BLOCK+LOG  │   ║
            │                              ║   │NON-SENSITIV?│   ║
            │                              ║   │→ ALLOW      │   ║
            │                              ║   └─────────────┘   ║
            │                              ╚══════════╤══════════╝
            │                                         │ Approved sanitized payload only
            │                                         ▼
            │                              ┌──────────────────────┐
            │                              │  CLOUD AI SERVICES   │
            │                              │  (Non-sensitive only) │
            │                              │  Cloud LLM (Claude)  │
            │                              │  Cloud ASR (fallback) │
            │                              └──────────────────────┘
            ▼
┌─────────────────────────────────────────────────────────────────────────────────────────┐
│                          [DATA LAYER — ON-PREMISE ONLY]                                │
│                                                                                         │
│  ┌──────────────────────┐   ┌──────────────────────┐   ┌──────────────────────────┐   │
│  │   PostgreSQL         │   │   MinIO Object Store  │   │   Redis (Session Cache)  │   │
│  │   (Encrypted at rest)│   │   (Documents, AES-256)│   │   (Context Vault)        │   │
│  │   RBAC, Audit trails │   │   RBAC, versioned     │   │   TTL-managed sessions   │   │
│  └──────────────────────┘   └──────────────────────┘   └──────────────────────────┘   │
│                                                                                         │
│  ┌──────────────────────────────────────────────────────────────────────────────────┐   │
│  │                 AUDIT LOG STREAM (Immutable, Separate from Ops Logs)             │   │
│  │                 OpenSearch / Loki → Grafana audit dashboard                      │   │
│  └──────────────────────────────────────────────────────────────────────────────────┘   │
└───────────────────────────────────┬─────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────────────────┐
│                            [OUTCOME ENGINE]                                             │
│  Receipt Generation → Status Update → Certificate Issuance → Channel Delivery          │
└─────────────────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────────────────┐
│                    [OPERATIONAL DASHBOARD]                                              │
│  Grafana + Prometheus: Latency · Error Rates · Anomaly Scores · Audit Completeness     │
└─────────────────────────────────────────────────────────────────────────────────────────┘
```

---

## 4. Full System Flow — End-to-End Journey

This section walks through a **complete income certificate journey** (the most common service) and shows every system interaction in sequence.

### 4.1 Journey: Income Certificate via WhatsApp (Voice Note → Hindi)

```
Step 1: CITIZEN INITIATES
──────────────────────────
Citizen: Sends a Hindi voice note to WhatsApp number:
         "Mujhe aay praman patra chahiye mere bete ki padhai ke liye"
         (I need an income certificate for my son's education)

Step 2: CHANNEL LAYER — WhatsApp Adapter
──────────────────────────────────────────
• Webhook receives the Twilio/Meta WhatsApp event
• Detects modality: VOICE (audio/ogg file attached)
• Sends audio to LOCAL ASR (Whisper): 
  → Transcription (local, never cloud): "mujhe aay praman patra chahiye mere bete ki padhai ke liye"
• Constructs ChannelMessage:
  {
    citizen_ref: "WA:+91-XXXXXXXXXX",  (resolved, not raw phone)
    channel_type: "WHATSAPP",
    modality: "VOICE",
    raw_text: "mujhe aay praman patra chahiye mere bete ki padhai ke liye",
    detected_lang: "hi",
    timestamp: "2026-08-19T09:00:00Z",
    session_hint: null  (new session)
  }

Step 3: CITIZEN RESOLVER
──────────────────────────
• Looks up citizen_ref in PostgreSQL
• If returning citizen: fetches profile, linked ID (tokenized)
• If new: creates anonymous citizen_ref, logs consent prompt required
• Resolves to ConversationSession or creates new one

Step 4: CONVERSATION ENGINE — NLU (Local LLM)
───────────────────────────────────────────────
• Phi-3 / Llama 3.1 8B (via Ollama, on-prem) processes the text:
  Intent:   CERTIFICATE_REQUEST
  Sub-intent: INCOME_CERTIFICATE
  Entities: {purpose: "education", beneficiary: "son"}
  Missing:  {applicant_name, applicant_dob, annual_income, address, id_proof}
  PII detected: none (utterance is intent-only, no raw PII yet)
  Literacy score: MEDIUM (complete sentence, clear intent)

Step 5: STATE MACHINE (LangGraph)
───────────────────────────────────
• Current state: INIT
• Intent match: INCOME_CERTIFICATE → transition to SLOT_FILLING
• Loads income_certificate.yaml from service catalogue
• Required slots: [applicant_name, dob, income_amount, address, aadhaar_ref, supporting_docs]
• Missing slots: all (new session)
• Next action: PROMPT_APPLICANT_NAME

Step 6: LITERACY-ADAPTIVE RESPONSE
──────────────────────────────────────
• Literacy score: MEDIUM
• Language: Hindi
• Response style: Simple Hindi, no complex vocabulary
• TTS (local Piper TTS): converts response to audio
• Channel Layer sends back via WhatsApp:
  Audio: "Aapka naam kya hai? Aadhar card mein jo naam hai woh batayein."
         (What is your name? Please tell the name as it appears on Aadhaar.)

Step 7: ITERATIVE SLOT FILLING (Repeat for each field)
────────────────────────────────────────────────────────
• Each citizen utterance → ASR (local) → NLU → Entity extraction → Slot fill
• State machine tracks filled/missing slots
• Context Vault persists after every exchange:
  ConversationState {
    service: "INCOME_CERTIFICATE",
    channel: "WHATSAPP",
    session_id: "sess_abc123",
    citizen_ref: "resolved_token_xyz",
    filled_slots: {name: "Ramesh Kumar", dob: "1985-03-15"},
    missing_slots: [income_amount, address, aadhaar_ref, docs],
    correction_history: [],
    literacy_level: "MEDIUM",
    language: "hi"
  }

Step 8: CHANNEL SWITCH — Citizen calls IVR
───────────────────────────────────────────
• Citizen calls IVR, provides their phone number / OTP
• IVR Adapter resolves citizen_ref from phone → matches existing session
• Context Manager loads ConversationState from Context Vault
• State machine resumes from: missing_slots: [income_amount, address, aadhaar_ref, docs]
• IVR Adapter: "Aapka aavedan shuru ho gaya hai. Abhi aapki aay ki jaankari chahiye."
  (Your application is in progress. Now I need your income information.)

Step 9: DOCUMENT UPLOAD TRIGGER
──────────────────────────────────
• Citizen told to send document via WhatsApp (channel switch back)
• WhatsApp receives image of income proof (salary slip / bank statement)
• Document Adapter invoked:
  → LayoutLMv3-class model (LOCAL, on-prem) extracts fields:
     {employer: "XYZ Corp", monthly_salary: 15000, period: "2025-2026"}
  → Cross-checks against conversationally declared income
  → Mismatch detected? → FLAG for manual review OR re-prompt citizen
  → Extracted fields written to MinIO (encrypted) + PostgreSQL metadata

Step 10: BUSINESS RULES VALIDATION
────────────────────────────────────
• income_certificate.yaml rules loaded:
  - income_amount: must be numeric, range 0–10,000,000
  - aadhaar_ref: must match 12-digit format (validated locally, not transmitted)
  - supporting_doc: required for income > 50,000/month
• LightGBM anomaly scorer checks:
  - Resubmission velocity (same citizen, multiple attempts in 1 hour?) → score: 0.12 (low risk)
  - Field mismatch rate between doc and conversational data → 0.08 (low)
  - Temporal pattern (application at 3am?) → 0.05 (low)
  - Composite anomaly score: 0.09 → PASS (threshold: 0.7)

Step 11: CONSENT CAPTURE
──────────────────────────
• System presents consent summary in Hindi (audio + text)
• Citizen explicitly says "haan" (yes) / presses 1 on IVR
• Consent record written to audit log (immutable, timestamped)

Step 12: PAYMENT FLOW
──────────────────────
• Fee calculated from fee schedule in service spec: ₹50 for income certificate
• Payment Adapter (mock for POC, real UPI/gateway in prod):
  → Generates payment link / UPI QR code
  → Sent to citizen via WhatsApp
  → Citizen pays → callback received → PaymentTransaction record created
• Payment receipt written to Data Layer

Step 13: DATA GUARD CHECK (Outbound call attempt)
───────────────────────────────────────────────────
• Orchestration Engine wants to use Cloud LLM to polish the final summary in Hindi
• Payload is assembled: {summary: "Income cert application for Ramesh Kumar, ₹50 paid..."}
• Data Guard (OPA/Rego) evaluates:
  → "Ramesh Kumar" → classified: RESTRICTED (PII)
  → BLOCK: payload contains restricted field
  → Audit log entry: {action: "BLOCK", reason: "PII in payload", field: "applicant_name", timestamp: ...}
• Local LLM used as fallback for language polishing instead

Step 14: SUBMISSION
────────────────────
• All slots filled, docs uploaded, payment confirmed, consent recorded
• Submission record assembled in Data Layer
• Assigned application number: APP-IC-2026-00123456
• Status: SUBMITTED

Step 15: OUTCOME ENGINE
────────────────────────
• Receipt generated (PDF): application number, summary, timestamp
• Sent to citizen via WhatsApp (and SMS notification as backup)
• Status tracking webhook registered: citizen can query status anytime
• Certificate issuance workflow triggered (mock adapter to government backend)

Step 16: STATUS QUERY (Future)
───────────────────────────────
• Citizen sends "mera status kya hai?" (What is my status?)
• NLU detects: STATUS_QUERY intent
• Status Agent retrieves from Data Layer: UNDER_REVIEW
• Citizen notified: "Aapka praman patra samiksha mein hai. 2-3 din mein update milega."
                    (Your certificate is under review. Update in 2-3 days.)
```

---

## 5. Component-Level Deep Dive

### 5.1 Channel Layer

The Channel Layer is the **only component that touches raw citizen input**. Its job is to normalize every channel into a single, channel-agnostic message format before anything else processes it.

#### 5.1.1 Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        CHANNEL LAYER                            │
│                                                                 │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │                  Channel Adapters                         │   │
│  │                                                           │   │
│  │  WhatsAppAdapter    IVRAdapter      WebAdapter   MobileApp│   │
│  │  (Meta/Twilio)      (Asterisk/      (FastAPI     (REST    │   │
│  │  Webhook receiver   FreeSWITCH)     WebSocket)   Push)    │   │
│  │       │                  │               │           │    │   │
│  │       │             Local ASR            │           │    │   │
│  │       │           (Whisper/faster-       │           │    │   │
│  │       │            whisper, on-prem)     │           │    │   │
│  └───────┴──────────────────┴───────────────┴───────────┘    │   │
│                             │                                   │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │                  Channel Normalizer                       │   │
│  │  Converts all inputs → ChannelMessage schema              │   │
│  │  Assigns/resolves citizen_ref (not device ID)             │   │
│  │  Language detection (langdetect + fastText local)         │   │
│  └──────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
```

#### 5.1.2 ChannelMessage Contract

```python
@dataclass
class ChannelMessage:
    citizen_ref: str           # Resolved, tokenized citizen identifier
    channel_type: ChannelType  # WHATSAPP | IVR | WEB | MOBILE
    modality: Modality         # VOICE | TEXT | DTMF | MIXED
    raw_text: str              # Transcribed or typed text
    raw_audio_ref: Optional[str]  # Local file ref if voice (never transmitted)
    detected_lang: str         # ISO 639-1 code: 'hi', 'ta', 'te', 'en', etc.
    timestamp: datetime
    session_hint: Optional[str]  # Session ID if resuming
    metadata: Dict[str, Any]   # Channel-specific metadata (masked)
```

#### 5.1.3 Local ASR Design

```
IVR Audio (raw PCM/GSM) → Whisper Tiny/Base (quantized, GGUF) → Raw Transcript
                                    │
                               Language ID
                                    │
                          Whisper Large-v3 (if needed for complex dialects)
                                    │
                              Clean Transcript
```

- **Whisper Tiny** (39M params): For clean audio, IVR DTMF bypass
- **Whisper Base** (74M params): Default for WhatsApp voice notes
- **faster-whisper**: CTranslate2 optimized, 4x faster on CPU
- **No cloud ASR** for raw audio — ever. Cloud ASR fallback only for synthetic/demo data.

#### 5.1.4 Supported Languages

| Language | ISO Code | ASR Model | TTS Model |
|---|---|---|---|
| Hindi | hi | Whisper + IndicASR fine-tune | Piper Hindi |
| Tamil | ta | Whisper + IndicASR | Piper Tamil |
| Telugu | te | Whisper + IndicASR | Piper Telugu |
| Kannada | kn | Whisper | Coqui Kannada |
| Marathi | mr | Whisper + IndicASR | Piper Marathi |
| Bengali | bn | Whisper | Piper Bengali |
| English | en | Whisper Base | Piper English |
| Code-mixed | hi-en | IndicASR (Jugalbandi) | Hybrid |

#### 5.1.5 IVR-Specific Design

```
DTMF Support:
  1 → "Apply for new certificate"
  2 → "Check application status"
  3 → "Speak to officer"
  * → "Repeat last message"
  # → "Main menu"

Voice Menu Flow:
  → Greeting in detected language
  → If no voice detected within 5s: DTMF fallback menu
  → If DTMF not pressed within 10s: Repeat prompt
  → After 3 failed attempts: Escalation to human officer
```

---

### 5.2 Conversation & Orchestration Engine

This is the **brain** of the platform. It houses the LangGraph state machine, multi-agent architecture, NLU pipeline, and Context Vault.

#### 5.2.1 Multi-Agent Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│                      MULTI-AGENT ORCHESTRATION                          │
│                         (LangGraph Framework)                           │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  ┌────────────────────────────────────────────────────────────────────┐ │
│  │                        SUPERVISOR AGENT                            │ │
│  │  Routes messages to appropriate specialist agent based on state     │ │
│  └─────────────────────────────┬──────────────────────────────────────┘ │
│                                │                                         │
│         ┌──────────────────────┼──────────────────────┐                 │
│         │                      │                      │                 │
│   ┌─────▼──────┐  ┌────────────▼─────┐  ┌────────────▼─────┐          │
│   │  INTAKE    │  │   VALIDATION     │  │    DOCUMENT      │          │
│   │   AGENT    │  │     AGENT        │  │     AGENT        │          │
│   │            │  │                  │  │                  │          │
│   │ Slot-fill  │  │ Rules check      │  │ Vision extract   │          │
│   │ Correction │  │ Eligibility      │  │ Cross-reference  │          │
│   │ Clarify    │  │ Anomaly flag     │  │ Mismatch detect  │          │
│   └─────┬──────┘  └────────────┬─────┘  └────────────┬─────┘          │
│         │                      │                      │                 │
│   ┌─────▼──────┐  ┌────────────▼─────┐  ┌────────────▼─────┐          │
│   │  PAYMENT   │  │   ESCALATION     │  │     STATUS       │          │
│   │   AGENT    │  │     AGENT        │  │     AGENT        │          │
│   │            │  │                  │  │                  │          │
│   │ Fee calc   │  │ RAG-grounded HO  │  │ Async polling    │          │
│   │ Link gen   │  │ Officer summary  │  │ Proactive push   │          │
│   │ Receipt    │  │ Ticket create    │  │ Status update    │          │
│   └────────────┘  └──────────────────┘  └──────────────────┘          │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
```

#### 5.2.2 LangGraph State Machine Nodes

```python
# State Machine Node Definitions
class ConversationState(TypedDict):
    service_type: str                    # e.g., "INCOME_CERTIFICATE"
    current_node: str                    # Active state machine node
    citizen_ref: str                     # Resolved citizen token
    channel: str                         # Current channel
    filled_slots: Dict[str, Any]         # Successfully extracted fields
    missing_slots: List[str]             # Yet to be collected
    validation_errors: List[str]         # Current validation issues
    correction_history: List[Dict]       # Past corrections with timestamps
    document_refs: List[str]             # MinIO object references
    payment_status: PaymentStatus        # PENDING | PAID | WAIVED | FAILED
    consent_given: bool                  # Explicit consent captured
    literacy_level: LiteracyLevel        # LOW | MEDIUM | HIGH
    language: str                        # Current language code
    anomaly_score: float                 # LightGBM anomaly score (0–1)
    escalation_reason: Optional[str]     # Set if escalation triggered
    session_ttl: datetime                # Session expiry for cleanup

# State Transitions
STATE_GRAPH = {
    "INIT": ["CONSENT", "RESUME_SESSION"],
    "CONSENT": ["INTENT_DETECTION"],
    "INTENT_DETECTION": ["SLOT_FILLING", "STATUS_QUERY", "ESCALATION"],
    "SLOT_FILLING": ["SLOT_FILLING", "DOCUMENT_CAPTURE", "VALIDATION"],
    "DOCUMENT_CAPTURE": ["DOCUMENT_VERIFY", "SLOT_FILLING"],
    "DOCUMENT_VERIFY": ["VALIDATION", "CORRECTION_PROMPT"],
    "VALIDATION": ["PAYMENT", "CORRECTION_PROMPT", "ESCALATION"],
    "CORRECTION_PROMPT": ["SLOT_FILLING", "DOCUMENT_CAPTURE"],
    "PAYMENT": ["SUBMISSION", "PAYMENT_RETRY", "ESCALATION"],
    "SUBMISSION": ["OUTCOME"],
    "OUTCOME": ["STATUS_QUERY", "END"],
    "STATUS_QUERY": ["END"],
    "ESCALATION": ["END"],
    "END": []
}
```

#### 5.2.3 Context Vault Design

```python
# Context Vault — Channel-Agnostic Session Store
class ContextVault:
    """
    Redis-backed, PostgreSQL-persisted session store.
    Key: citizen_ref (NOT channel-specific session ID)
    Enables seamless channel switching without state loss.
    """

    def load_session(self, citizen_ref: str) -> ConversationState:
        # 1. Check Redis (hot cache, TTL: 30 min)
        # 2. Fallback to PostgreSQL (persistent, encrypted)
        # 3. If neither: create new session
        pass

    def save_session(self, citizen_ref: str, state: ConversationState) -> None:
        # Atomic write: Redis (async) + PostgreSQL (synchronous, authoritative)
        pass

    def transfer_channel(self, citizen_ref: str, new_channel: str) -> ConversationState:
        # Load existing state, update channel field, save
        # State machine continues from where it was — channel is just metadata
        pass
```

#### 5.2.4 Literacy-Adaptive Dialogue System

```python
class LiteracyAdaptiveDialogue:
    """
    Dynamically adjusts response complexity, vocabulary, 
    and prompt structure based on detected literacy level.
    """

    LOW_LITERACY_PATTERNS = [
        "one_word_answers",
        "frequent_clarification_requests",
        "very_short_utterances",
        "DTMF_preference"
    ]

    ADAPTATION_RULES = {
        LiteracyLevel.LOW: {
            "max_words_per_prompt": 15,
            "use_examples": True,
            "prefer_dtmf": True,
            "repeat_confirmation": True,
            "vocabulary": "basic",
            "sentence_structure": "simple"
        },
        LiteracyLevel.MEDIUM: {
            "max_words_per_prompt": 30,
            "use_examples": False,
            "prefer_dtmf": False,
            "repeat_confirmation": False,
            "vocabulary": "standard",
            "sentence_structure": "compound"
        },
        LiteracyLevel.HIGH: {
            "max_words_per_prompt": 60,
            "use_examples": False,
            "prefer_dtmf": False,
            "repeat_confirmation": False,
            "vocabulary": "formal",
            "sentence_structure": "complex"
        }
    }
```

---

### 5.3 Business & Rules Engine

The Rules Engine is the **compliance core** — deterministic, config-driven, and free of LLM ambiguity.

#### 5.3.1 Declarative Service Specification Format

```yaml
# income_certificate.yaml
service:
  id: "INCOME_CERTIFICATE"
  name:
    en: "Income Certificate"
    hi: "आय प्रमाण पत्र"
    ta: "வருமான சான்று"
  department: "Revenue Department"
  sla_days: 3
  fee:
    amount: 50
    currency: "INR"
    waiver_conditions:
      - condition: "annual_income < 20000"
        waiver_percent: 100
      - condition: "bpl_card == true"
        waiver_percent: 100

slots:
  - name: applicant_name
    type: string
    required: true
    validation:
      regex: "^[a-zA-Z\u0900-\u097F ]{3,100}$"
      min_length: 3
    prompt:
      hi: "आवेदक का पूरा नाम बताएं"
      en: "Please tell the applicant's full name"

  - name: annual_income
    type: number
    required: true
    validation:
      min: 0
      max: 10000000
      integer_only: false
    prompt:
      hi: "वार्षिक आय कितनी है? (रुपए में)"
      en: "What is the annual income? (in Rupees)"

  - name: aadhaar_number
    type: string
    required: true
    classification: RESTRICTED      # ← Data Guard will block this from cloud
    validation:
      regex: "^[0-9]{12}$"
      luhn_check: true
    prompt:
      hi: "आधार कार्ड नंबर बताएं"
      en: "Please provide the Aadhaar card number"

  - name: address
    type: address
    required: true
    sub_fields:
      - house_number
      - street
      - village_or_ward
      - district
      - state
      - pincode

documents:
  required:
    - type: IDENTITY_PROOF
      accepted: [AADHAAR, PAN, VOTER_ID, PASSPORT]
    - type: INCOME_PROOF
      accepted: [SALARY_SLIP, BANK_STATEMENT, EMPLOYER_LETTER]
  optional:
    - type: BPL_CARD
      condition: "annual_income < 20000"

eligibility:
  - rule: "applicant_age >= 18"
    error:
      hi: "आवेदक की आयु 18 वर्ष से अधिक होनी चाहिए"
      en: "Applicant must be 18 years or older"
  - rule: "address.state == 'state_of_jurisdiction'"
    error:
      hi: "आवेदक इस राज्य का निवासी होना चाहिए"
      en: "Applicant must be a resident of this state"

cross_field_validations:
  - rule: "doc_extracted_income BETWEEN annual_income * 0.8 AND annual_income * 1.2"
    severity: WARNING
    message: "Declared income differs significantly from document"
```

#### 5.3.2 LightGBM Fraud/Anomaly Scorer

```python
# Features fed to LightGBM fraud scorer
ANOMALY_FEATURES = [
    "resubmission_count_1h",          # How many times submitted in last hour
    "resubmission_count_24h",         # Same in 24h
    "field_mismatch_rate",            # % fields differing from document extraction
    "application_hour",               # Hour of day (0–23)
    "correction_count",               # Number of corrections made
    "session_duration_seconds",       # Time taken to fill form
    "channel_switches",               # Number of times channel was switched
    "doc_to_speech_income_delta",     # Absolute difference in income values
    "aadhaar_lookup_count",           # Prior lookups for this Aadhaar ref
    "ip_application_velocity",        # Applications from same IP range
]

# Model: Gradient Boosted Trees
# Training data: Synthetic persona submissions (good + adversarial)
# Threshold: 0.7 → flag for manual review
# Output: {score: float, top_features: List[str], decision: PASS|REVIEW|REJECT}
```

#### 5.3.3 Fee Calculator

```python
class FeeCalculator:
    def calculate(self, service_id: str, citizen_data: Dict) -> FeeResult:
        spec = self.load_spec(service_id)
        base_fee = spec.fee.amount

        # Check waiver conditions (ordered by priority)
        for waiver in spec.fee.waiver_conditions:
            if self.evaluate_rule(waiver.condition, citizen_data):
                discount = base_fee * (waiver.waiver_percent / 100)
                return FeeResult(
                    base_fee=base_fee,
                    discount=discount,
                    final_fee=base_fee - discount,
                    waiver_reason=waiver.condition
                )
        return FeeResult(base_fee=base_fee, discount=0, final_fee=base_fee)
```

---

### 5.4 Service Adapters

Each adapter follows the **Adapter Pattern** — mock and real implementations are interchangeable via config. For the POC, mocks are the default; real integrations are plug-ins.

#### 5.4.1 Adapter Interface Contracts

```python
# Base interface all adapters implement
class BaseAdapter(ABC):
    @abstractmethod
    def execute(self, request: BaseRequest) -> BaseResponse:
        pass

    @abstractmethod
    def health_check(self) -> HealthStatus:
        pass

    @abstractmethod
    def get_capabilities(self) -> AdapterCapabilities:
        pass

# Auth Adapter
class AuthAdapter(BaseAdapter):
    def execute(self, request: AuthRequest) -> AuthResponse:
        # OTP verification / Biometric / DigiLocker
        pass

class MockAuthAdapter(AuthAdapter):
    def execute(self, request: AuthRequest) -> AuthResponse:
        # Simulates OTP: always succeeds for test OTP "123456"
        return AuthResponse(success=True, auth_token="mock_token_xyz")

# Document Adapter
class DocumentAdapter(BaseAdapter):
    def execute(self, request: DocumentRequest) -> DocumentResponse:
        # Calls local LayoutLMv3 for OCR/field extraction
        pass

# Payment Adapter
class PaymentAdapter(BaseAdapter):
    def execute(self, request: PaymentRequest) -> PaymentResponse:
        # UPI / Credit card / Cash at counter
        pass

class MockPaymentAdapter(PaymentAdapter):
    def execute(self, request: PaymentRequest) -> PaymentResponse:
        # Always returns success for amounts < 1000 (test threshold)
        return PaymentResponse(
            success=True,
            transaction_id=f"MOCK-TXN-{uuid4()}",
            receipt_url="mock://receipt/12345"
        )
```

#### 5.4.2 Document Intelligence Pipeline (Document Adapter Internal)

```
Document Upload (Image/PDF)
         │
         ▼
Pre-processing (local)
  → Image quality check (blur detection, resolution check)
  → Format conversion (PDF → PNG pages)
  → Orientation correction (deskew)
         │
         ▼
Layout Detection (LayoutLMv3-class model, local)
  → Identifies form regions, tables, text blocks
  → Assigns semantic labels (HEADER, FIELD_NAME, FIELD_VALUE, SIGNATURE, STAMP)
         │
         ▼
Field Extraction
  → Key-value pairs extracted from form regions
  → Named Entity Recognition on text blocks
  → Structured output: {name: "Ramesh Kumar", income: 15000, period: "2025-26"}
         │
         ▼
Cross-Reference Check
  → Compare extracted fields vs. conversationally declared values
  → Flag mismatches with severity (WARNING vs. ERROR)
  → Decision: PASS | MANUAL_REVIEW | REJECT
         │
         ▼
Write to Data Layer
  → Document stored in MinIO (AES-256 encrypted)
  → Metadata + extracted fields in PostgreSQL
  → Audit log entry created
```

#### 5.4.3 Escalation Adapter — RAG-Grounded Handoff

```python
class EscalationAdapter(BaseAdapter):
    """
    When a citizen needs human officer intervention,
    this adapter generates a RAG-grounded summary for the officer.
    """

    def execute(self, request: EscalationRequest) -> EscalationResponse:
        # 1. Retrieve conversation history from Context Vault
        history = self.context_vault.get_history(request.citizen_ref)

        # 2. Retrieve relevant service rules via RAG
        rules = self.rag_retriever.get_relevant_rules(
            service_type=request.service_type,
            issue_description=request.escalation_reason
        )

        # 3. Generate officer handoff summary (local LLM — NOT cloud)
        summary = self.local_llm.generate(
            prompt=ESCALATION_SUMMARY_PROMPT.format(
                history=history,
                rules=rules,
                issue=request.escalation_reason
            )
        )

        # 4. Create escalation ticket
        ticket = self.ticket_system.create(
            citizen_ref=request.citizen_ref,
            summary=summary,
            priority=self.calculate_priority(request),
            context=history
        )

        return EscalationResponse(
            ticket_id=ticket.id,
            officer_summary=summary,
            estimated_resolution_time="2 business days"
        )
```

---

### 5.5 Data Guard (Trust Boundary)

This is the **most important component** for the marking scheme (4/10 for Enterprise Architecture & Data Isolation). It must be demoable live.

#### 5.5.1 OPA/Rego Policy Engine

```rego
# data_guard_policy.rego
package dataguard

import future.keywords.in

# Data Classification Schema
restricted_fields := {
    "aadhaar_number",
    "pan_number",
    "voter_id",
    "passport_number",
    "bank_account",
    "date_of_birth",
    "biometric_data",
    "medical_history",
    "applicant_name",           # Name is PII when combined with application context
    "father_name",
    "mother_name",
    "address.house_number",
    "address.street",
    "phone_number",
    "email_address"
}

quasi_identifier_fields := {
    "district",
    "annual_income",
    "caste_category",
    "occupation",
    "age_range"
}

# Main policy: deny unless explicitly safe
default allow := false

# Allow if no restricted or quasi-identifier fields found in payload
allow if {
    count(restricted_in_payload) == 0
    count(quasi_id_in_payload) == 0
}

# Allow quasi-identifiers only if explicitly flagged as synthetic/demo data
allow if {
    count(restricted_in_payload) == 0
    input.data_classification == "SYNTHETIC"
    count(quasi_id_in_payload) < 3    # k-anonymity minimum
}

# Compute which restricted fields are present
restricted_in_payload := fields if {
    fields := {field |
        field := restricted_fields[_]
        _deep_contains(input.payload, field)
    }
}

quasi_id_in_payload := fields if {
    fields := {field |
        field := quasi_identifier_fields[_]
        _deep_contains(input.payload, field)
    }
}

# Recursively check nested payloads
_deep_contains(obj, key) if {
    _ = obj[key]
}
_deep_contains(obj, key) if {
    child = obj[_]
    is_object(child)
    _deep_contains(child, key)
}

# Generate block reason message
block_reason := msg if {
    not allow
    restricted := restricted_in_payload
    msg := sprintf("BLOCKED: Restricted fields detected: %v", [restricted])
}
```

#### 5.5.2 Data Guard Middleware

```python
class DataGuardMiddleware:
    """
    Intercepts ALL outbound calls to cloud services.
    Enforces OPA/Rego policy before any cloud call proceeds.
    """

    def __init__(self, opa_url: str, audit_logger: AuditLogger):
        self.opa = OPAClient(opa_url)
        self.audit = audit_logger

    def check_and_allow(
        self,
        payload: Dict,
        destination: str,
        caller: str,
        operation: str
    ) -> DataGuardResult:
        # 1. Evaluate OPA policy
        result = self.opa.evaluate(
            policy="dataguard",
            input={
                "payload": payload,
                "destination": destination,
                "caller": caller,
                "operation": operation
            }
        )

        # 2. Create immutable audit log entry
        audit_entry = AuditEntry(
            timestamp=datetime.utcnow(),
            action="ALLOW" if result.allow else "BLOCK",
            caller=caller,
            destination=destination,
            operation=operation,
            restricted_fields_found=result.restricted_in_payload,
            block_reason=result.block_reason if not result.allow else None,
            payload_hash=sha256(str(payload).encode()).hexdigest()
        )
        self.audit.write(audit_entry)

        if not result.allow:
            raise DataGuardBlockedError(
                reason=result.block_reason,
                blocked_fields=result.restricted_in_payload
            )

        return DataGuardResult(allowed=True, sanitized_payload=payload)
```

#### 5.5.3 Live Demo Scenario for Data Guard

```
DEMO SEQUENCE (demoable in under 60 seconds):

1. Dashboard shows: "Data Guard: 0 blocks today"

2. Deliberately craft a payload:
   payload = {
     "message": "Translate this to Tamil",
     "applicant_name": "Ramesh Kumar",   ← RESTRICTED FIELD
     "service": "income_certificate"
   }

3. Attempt cloud LLM call with this payload

4. Data Guard intercepts:
   → OPA policy evaluates
   → "applicant_name" found → RESTRICTED
   → BLOCK + AUDIT LOG written in real time

5. Dashboard updates: "Data Guard: 1 block today"
   → Click to see: {timestamp, caller, blocked_fields: ["applicant_name"], ...}

6. Show retry with sanitized payload:
   payload = {
     "message": "Translate 'income certificate service' to Tamil",
     "service": "income_certificate"
   }
   → ALLOWED → Cloud LLM call proceeds
```

---

### 5.6 Data Layer

#### 5.6.1 PostgreSQL Schema (Key Tables)

```sql
-- Citizens (tokenized, no raw PII in primary table)
CREATE TABLE citizens (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    citizen_ref VARCHAR(64) UNIQUE NOT NULL,    -- Resolved token, not raw ID
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Applications
CREATE TABLE applications (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    application_number VARCHAR(32) UNIQUE NOT NULL,
    citizen_ref VARCHAR(64) NOT NULL REFERENCES citizens(citizen_ref),
    service_type VARCHAR(64) NOT NULL,
    status VARCHAR(32) NOT NULL DEFAULT 'DRAFT',
    submitted_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ,
    anomaly_score DECIMAL(5,4),
    payment_status VARCHAR(32) DEFAULT 'PENDING',
    channel_origin VARCHAR(32) NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Encrypted application data (form fields)
CREATE TABLE application_data (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    application_id UUID NOT NULL REFERENCES applications(id),
    field_name VARCHAR(128) NOT NULL,
    field_value_encrypted BYTEA NOT NULL,    -- AES-256-GCM encrypted
    classification VARCHAR(32) NOT NULL,      -- RESTRICTED | QUASI | NON_SENSITIVE
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Documents (metadata only; file in MinIO)
CREATE TABLE documents (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    application_id UUID NOT NULL REFERENCES applications(id),
    doc_type VARCHAR(64) NOT NULL,
    minio_object_ref VARCHAR(512) NOT NULL,   -- Encrypted path in MinIO
    extracted_fields JSONB,                   -- OCR output (also encrypted)
    verification_status VARCHAR(32) DEFAULT 'PENDING',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Payments
CREATE TABLE payment_transactions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    application_id UUID NOT NULL REFERENCES applications(id),
    transaction_id VARCHAR(128) UNIQUE NOT NULL,
    amount DECIMAL(10,2) NOT NULL,
    currency VARCHAR(8) DEFAULT 'INR',
    status VARCHAR(32) NOT NULL,
    gateway VARCHAR(64),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Immutable Audit Log (append-only, separate tablespace)
CREATE TABLE audit_log (
    id BIGSERIAL PRIMARY KEY,
    event_type VARCHAR(64) NOT NULL,
    actor VARCHAR(128),
    citizen_ref VARCHAR(64),
    application_id UUID,
    action VARCHAR(256) NOT NULL,
    outcome VARCHAR(32) NOT NULL,   -- ALLOW | BLOCK | SUCCESS | FAILURE
    metadata JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
) TABLESPACE audit_tblspc;

-- Prevent updates/deletes on audit log
CREATE RULE audit_log_no_update AS ON UPDATE TO audit_log DO INSTEAD NOTHING;
CREATE RULE audit_log_no_delete AS ON DELETE TO audit_log DO INSTEAD NOTHING;

-- Conversation sessions (Redis hot, PG cold)
CREATE TABLE conversation_sessions (
    session_id VARCHAR(128) PRIMARY KEY,
    citizen_ref VARCHAR(64) NOT NULL,
    state JSONB NOT NULL,                     -- Full ConversationState serialized
    last_channel VARCHAR(32) NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    expires_at TIMESTAMPTZ NOT NULL
);
```

#### 5.6.2 Encryption Strategy

```
At Rest:
  PostgreSQL: AES-256-GCM via pgcrypto extension
  MinIO: Server-side encryption (SSE-KMS) with local KMS (HashiCorp Vault or Sealed Box)
  Redis: Encrypted RDB persistence

In Transit:
  All internal service communication: mTLS (mutual TLS)
  API Gateway: TLS 1.3
  No plaintext channels within the trust boundary

Key Management:
  Master key: Hardware Security Module (HSM) or Sealed Box for POC
  Application keys: Rotated every 90 days
  Audit log: Separate encryption key (read-only for operations, audit officer only for decrypt)
```

#### 5.6.3 MinIO Object Storage Structure

```
minio://
├── documents/
│   ├── {application_id}/
│   │   ├── identity_proof_{uuid}.pdf.enc
│   │   ├── income_proof_{uuid}.jpg.enc
│   │   └── metadata.json.enc
├── audio/
│   ├── {session_id}/
│   │   └── utterance_{timestamp}.wav.enc   (kept for 7 days, then purged)
├── receipts/
│   ├── {application_number}/
│   │   └── receipt.pdf.enc
└── certificates/
    └── issued/
        └── {application_number}/
            └── certificate.pdf.enc
```

---

### 5.7 Outcome Engine

```python
class OutcomeEngine:
    """
    Handles the final phase of every service journey:
    receipt generation, status tracking, certificate issuance, 
    and proactive citizen communication.
    """

    def process_submission(self, application_id: str) -> OutcomeResult:
        app = self.db.get_application(application_id)

        # 1. Generate receipt
        receipt = self.receipt_generator.generate(app)
        receipt_ref = self.storage.store_encrypted(receipt)

        # 2. Update application status
        self.db.update_status(application_id, ApplicationStatus.SUBMITTED)

        # 3. Trigger certificate workflow (mock adapter)
        workflow_result = self.certificate_adapter.trigger_workflow(app)

        # 4. Deliver receipt through the current channel
        # Key: uses Context Vault to find CURRENT channel (may differ from origin)
        current_channel = self.context_vault.get_current_channel(app.citizen_ref)
        self.channel_layer.send(
            citizen_ref=app.citizen_ref,
            channel=current_channel,
            message=ReceiptMessage(
                application_number=app.application_number,
                receipt_url=receipt_ref,
                estimated_completion=self.sla_calculator.estimate(app)
            )
        )

        # 5. Schedule proactive status updates (async)
        self.status_scheduler.schedule(
            application_id=application_id,
            citizen_ref=app.citizen_ref,
            check_interval_hours=24
        )

        return OutcomeResult(
            application_number=app.application_number,
            receipt_ref=receipt_ref,
            status=ApplicationStatus.SUBMITTED
        )
```

---

### 5.8 Operational Dashboard

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                      REVENUE SERVICES — OPERATIONS DASHBOARD                    │
│                              Grafana v10 | Prometheus Datasource                │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                 │
│  REAL-TIME METRICS                      CHANNEL BREAKDOWN                       │
│  ┌──────────────────────────────┐       ┌──────────────────────────────────┐    │
│  │ Active Sessions:      142    │       │ WhatsApp:  ████████░░░ 68%       │    │
│  │ Submitted Today:      89     │       │ IVR:       ████░░░░░░ 22%        │    │
│  │ Avg Latency (NLU):   180ms  │       │ Web:       ██░░░░░░░░ 8%         │    │
│  │ Error Rate:          0.8%   │       │ Mobile:    █░░░░░░░░░ 2%         │    │
│  └──────────────────────────────┘       └──────────────────────────────────┘    │
│                                                                                 │
│  DATA GUARD STATUS                      ANOMALY SCORES                          │
│  ┌──────────────────────────────┐       ┌──────────────────────────────────┐    │
│  │ Blocks Today:         3      │       │ High Risk (>0.7):   2 apps       │    │
│  │ Allows Today:         456    │       │ Medium Risk (0.4-0.7): 5 apps   │    │
│  │ Audit Entries:        459    │       │ Low Risk (<0.4):  82 apps        │    │
│  │ Last Block:    09:14:22     │       │ Avg Score:  0.12                 │    │
│  └──────────────────────────────┘       └──────────────────────────────────┘    │
│                                                                                 │
│  SERVICE BREAKDOWN                      LANGUAGE DISTRIBUTION                   │
│  ┌──────────────────────────────┐       ┌──────────────────────────────────┐    │
│  │ Income Cert:   45 apps       │       │ Hindi:     ██████░░ 48%          │    │
│  │ Caste Cert:    18 apps       │       │ Telugu:    ████░░░░ 28%          │    │
│  │ Domicile:      12 apps       │       │ Tamil:     ███░░░░░ 18%          │    │
│  │ Nativity:       8 apps       │       │ English:   █░░░░░░░ 6%           │    │
│  │ Solvency:       6 apps       │       └──────────────────────────────────┘    │
│  └──────────────────────────────┘                                               │
└─────────────────────────────────────────────────────────────────────────────────┘
```

---

## 6. AI & ML Layer — Model-by-Model Breakdown

### 6.1 NLU — Local Language Model

| Attribute | Detail |
|---|---|
| **Model** | Llama 3.1 8B (quantized GGUF Q4_K_M) or Phi-3 Mini (3.8B, Q4) |
| **Runtime** | Ollama or llama.cpp (CPU-capable), VRAM optional |
| **Tasks** | Intent classification, entity extraction, PII tagging, language-agnostic understanding |
| **Why local?** | All citizen utterances contain potential PII — they can never reach cloud |
| **Latency** | ~800ms on CPU (4 cores) / ~150ms on GPU |
| **Fine-tuning** | Prompt-engineered for Indian government domain; LoRA fine-tune optional for production |
| **Multilingual** | Natively multilingual; handles code-mixing (Hindi-English) without special handling |
| **Fallback** | If model is down: rule-based keyword intent matcher (always available) |

### 6.2 ASR — Automatic Speech Recognition

| Attribute | Detail |
|---|---|
| **Primary Model** | faster-whisper (CTranslate2-optimized Whisper), Base or Small variant |
| **Language support** | 99 languages including all major Indian languages |
| **Runtime** | CPU-optimized, ~2.5x realtime on modern CPU |
| **Dialect handling** | Whisper is reasonably robust; IndicASR (Vakyansh) as domain-specific option |
| **IVR integration** | Real-time streaming via WebRTC audio capture → local ASR |
| **Audio quality** | Handles WhatsApp OGG (opus), IVR GSM, web WebM formats |
| **Cloud ASR** | NEVER for real citizen audio; cloud ASR only for synthetic demo data |

### 6.3 TTS — Text-to-Speech

| Attribute | Detail |
|---|---|
| **Primary Model** | Piper TTS (local, fast, multilingual) |
| **Languages** | Hindi, Tamil, Telugu, Kannada, Marathi, Bengali, English |
| **Quality** | Neural TTS, ONNX-optimized, ~0.5 RTF on CPU |
| **Voice styles** | Formal (officer), Friendly (citizen-facing), Urgent (alerts) |
| **SSML support** | Custom prompts, pauses, emphasis for IVR |
| **Coqui TTS** | Backup option for languages not covered by Piper |

### 6.4 Document Intelligence — Vision Model

| Attribute | Detail |
|---|---|
| **Model** | LayoutLMv3 (Microsoft) or DocTR (mindee) |
| **Tasks** | Form field extraction, table parsing, key-value extraction |
| **Why local?** | Documents contain dense PII — Aadhaar, PAN, name, DOB, address |
| **Input formats** | PDF, JPEG, PNG, TIFF |
| **Pre-processing** | OpenCV for deskew, quality check; pypdf2 for PDF rendering |
| **Supported docs** | Aadhaar, PAN card, Voter ID, salary slip, bank statement, ration card |
| **Accuracy** | ~92% field extraction accuracy for printed docs, ~78% handwritten |
| **Confidence scoring** | Every extracted field has a confidence score; low-confidence → re-prompt |

### 6.5 Fraud Detection — LightGBM

| Attribute | Detail |
|---|---|
| **Model** | LightGBM Gradient Boosted Trees (scikit-learn compatible) |
| **Input features** | 10 behavioral + temporal features (see section 5.3.2) |
| **Training data** | Synthetic persona submissions (balanced: normal + adversarial) |
| **Inference** | <5ms per scoring call |
| **Explainability** | SHAP values for each prediction (shows which features drove the score) |
| **Thresholds** | <0.4: PASS, 0.4–0.7: MANUAL_REVIEW, >0.7: REJECT |
| **Retraining** | Weekly batch retraining on new submission data (SMOTE for class balance) |

### 6.6 RAG — Retrieval-Augmented Generation

| Attribute | Detail |
|---|---|
| **Vector Store** | ChromaDB (local, persistent) or FAISS (in-memory, faster) |
| **Embedding Model** | sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2 (local) |
| **Knowledge Base** | Service rulebooks, government circulars, FAQ documents (seeded) |
| **Use Cases** | Escalation summaries, eligibility guidance, correction suggestions |
| **Retrieval** | Top-K similarity search (K=5), re-ranked by cross-encoder |
| **Generation** | Local LLM generates based on retrieved context |
| **Update Strategy** | New documents indexed on upload without full rebuild |

### 6.7 Cloud LLM (Data-Guard Gated)

| Attribute | Detail |
|---|---|
| **Model** | Claude 3.5 Haiku or GPT-4o Mini (cost-optimized) |
| **Allowed tasks** | Multilingual phrasing polish, synthetic data generation, translation of non-sensitive strings |
| **Gateway** | ALL calls go through Data Guard — no direct API calls |
| **What it NEVER sees** | Citizen names, IDs, addresses, documents, financial data |
| **Prompt design** | All prompts use placeholders: "Translate 'income certificate' to [language]" |
| **Rate limiting** | Max 100 calls/day per environment (cost control) |

---

## 7. Complete Technology Stack & Justifications

### 7.1 Backend Infrastructure

| Component | Technology | Version | Why This Choice |
|---|---|---|---|
| **API Framework** | FastAPI (Python) | 0.115+ | Async, OpenAPI-native, strong typing with Pydantic, best-in-class for AI/ML APIs |
| **State Machine** | LangGraph | 0.2+ | Purpose-built for multi-agent conversation flows; native LangChain integration; graph-based state management |
| **Task Queue** | Celery + Redis | Celery 5.3 | Async document processing, payment callbacks, status updates — proven at scale |
| **Message Broker** | Redis | 7.x | Also serves as Context Vault hot cache; sub-millisecond session reads |
| **API Gateway** | Kong or Nginx + Lua | Kong 3.x | Rate limiting, auth, TLS termination, routing to services |
| **Service Discovery** | Consul | 1.17+ | On-prem-ready service discovery; health checks for all adapters |
| **Secret Management** | HashiCorp Vault | 1.15+ | Encrypts at rest, audit logs all secret access, on-prem deployable |

### 7.2 AI/ML Runtime

| Component | Technology | Why |
|---|---|---|
| **Local LLM runtime** | Ollama + llama.cpp | CPU-capable, easy model management, Modelfile for reproducibility |
| **LLM models** | Llama 3.1 8B / Phi-3 Mini (GGUF Q4) | Balance of quality and on-prem resource constraints |
| **ASR** | faster-whisper | 4x faster than OpenAI Whisper on CPU; streaming support |
| **TTS** | Piper TTS | Offline, multilingual, ONNX-optimized, <200ms latency |
| **Vision/OCR** | LayoutLMv3 + DocTR | Layout-aware; understands form structure, not just text |
| **Embeddings** | sentence-transformers | Multilingual, local, no cloud needed |
| **Vector DB** | ChromaDB | Local-first, persistent, easy to set up and seed |
| **ML Framework** | scikit-learn + LightGBM | Industry standard for tabular ML; LightGBM is fast and explainable |
| **Policy Engine** | OPA (Open Policy Agent) | Industry-standard policy enforcement; Rego is auditable |

### 7.3 Frontend

| Component | Technology | Why |
|---|---|---|
| **Web Portal** | Next.js 14 (React 18) | SSR for performance, strong TypeScript support, easy API integration |
| **Mobile App** | React Native | Code-sharing with web, cross-platform iOS/Android |
| **UI Components** | shadcn/ui + Tailwind | Accessible, customizable, government-friendly design system |
| **Real-time** | Socket.io / WebSocket | Status updates, live conversation continuity |
| **Audio** | Web Audio API | Browser-based voice recording without plugins |
| **Internationalization** | react-i18next | 8 Indian language support with right-to-left fallback |

### 7.4 Data & Storage

| Component | Technology | Why |
|---|---|---|
| **Primary DB** | PostgreSQL 16 | ACID, row-level security, pgcrypto for encryption, proven for government |
| **Object Storage** | MinIO | S3-compatible, on-prem, AES-256 encryption, RBAC |
| **Session Cache** | Redis 7 | Sub-millisecond, TTL management, persistence for crash recovery |
| **Search** | OpenSearch | Audit log search, full-text search on applications |
| **Migrations** | Alembic | Version-controlled schema changes, reproducible setup |

### 7.5 Observability

| Component | Technology | Why |
|---|---|---|
| **Metrics** | Prometheus + Grafana | Industry standard; pre-built dashboards for FastAPI, Redis, PostgreSQL |
| **Tracing** | OpenTelemetry + Jaeger | Distributed tracing across all microservices |
| **Logging (Ops)** | Loki + Grafana | Log aggregation without Elasticsearch complexity |
| **Logging (Audit)** | OpenSearch (separate index) | Immutable audit logs; separate from operational logs |
| **Alerting** | Grafana Alerting | PagerDuty/Slack integration for on-call |
| **Uptime** | Prometheus Blackbox | Endpoint health monitoring |

### 7.6 DevOps & Infrastructure

| Component | Technology | Why |
|---|---|---|
| **Containerization** | Docker + Docker Compose | Reproducible, portable, all services in one `docker-compose up` |
| **Orchestration** | Kubernetes (k3s for local) | On-prem-ready; k3s is lightweight for single-node POC |
| **CI/CD** | GitHub Actions | Free, YAML-based, integrates with all tools |
| **Linting** | Ruff (Python) + ESLint (JS) | Fast, configurable, pre-commit hooks |
| **Type Checking** | mypy (Python) + TypeScript | Catches type errors before runtime |
| **Testing** | pytest + Jest | pytest for Python, Jest for React |
| **Coverage** | coverage.py + Istanbul | Enforce minimum coverage thresholds |
| **Pre-commit** | pre-commit hooks | Linting, formatting, secrets scanning before commit |
| **Secret Scanning** | git-secrets + detect-secrets | Prevents API keys in commits |
| **IaC** | Ansible or shell scripts | Reproducible server setup for on-prem deployment |

---

## 8. Data Sovereignty & Security Architecture

### 8.1 Data Classification Framework

```
CLASSIFICATION LEVELS:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

LEVEL 1: RESTRICTED (🔴 NEVER leaves on-premise)
─────────────────────────────────────────────────
• Aadhaar number, PAN, Voter ID, Passport number
• Citizen name, date of birth, phone number, email
• Residential address (house number + street)
• Bank account details, financial records
• Biometric data (fingerprint, iris)
• Application form field values
• Uploaded documents and extracted OCR data
• Session conversation history

LEVEL 2: QUASI-IDENTIFIER (🟡 Aggregated use only)
────────────────────────────────────────────────────
• District name, age range (not exact DOB)
• Income bracket (not exact amount)
• Caste category, occupation type
• Application status (not linked to citizen identity)
These can only travel in aggregate (k≥5 anonymized sets), never individually.

LEVEL 3: NON-SENSITIVE (🟢 May go to cloud via Data Guard)
──────────────────────────────────────────────────────────────
• Service names ("income certificate", "caste certificate")
• Generic UI strings needing translation
• Synthetic/demo personas (explicitly labeled)
• Error messages, help text
• Operational metrics (counts, percentages)
```

### 8.2 Trust Boundary Enforcement Points

```
ENFORCEMENT CHECKPOINTS:
1. Channel Layer → NLU: Audio stays local (ASR on-prem)
2. NLU → Context Manager: PII tagged but not transmitted anywhere
3. Context Manager → Business Rules: Citizen ref tokens, not raw IDs
4. Service Adapters → Cloud: Data Guard blocks any restricted field
5. Audit Logger: Separate from ops logs; all decisions recorded
6. MinIO/PostgreSQL: Encrypted at rest; RBAC on all access
7. API Gateway: All external access authenticated + rate-limited
```

### 8.3 Security Controls Matrix

| Control | Implementation | Verification |
|---|---|---|
| Data-at-rest encryption | AES-256-GCM (pgcrypto + MinIO SSE) | Decrypt test in CI |
| Data-in-transit encryption | mTLS between services, TLS 1.3 external | SSL Labs test |
| Access control | PostgreSQL Row-Level Security + API Gateway RBAC | Penetration test |
| Secret management | HashiCorp Vault | Secret rotation test |
| PII detection | OPA/Rego policy + regex classifiers | Adversarial test suite |
| Audit logging | Append-only PostgreSQL table + OpenSearch | Audit completeness test |
| Input validation | Pydantic models at every API boundary | Fuzzing tests |
| Rate limiting | Kong rate limiting plugin | Load test |
| Session management | Redis with TTL + PostgreSQL persistence | Session hijack test |
| Key rotation | Automated 90-day rotation | Key rotation test |

---

## 9. Conversation State Machine Design

### 9.1 Complete State Transition Diagram

```
                         ┌─────────────────────────────────┐
                         │          CITIZEN INPUT           │
                         └──────────────┬──────────────────┘
                                        │
                         ┌──────────────▼──────────────────┐
                         │              INIT               │
                         │  (New session OR resume check)  │
                         └──────┬───────────────┬──────────┘
                     New session │       Resume  │
                                 │               │
                    ┌────────────▼────┐   ┌──────▼───────────────┐
                    │    CONSENT      │   │   RESUME_SESSION     │
                    │  (Capture user  │   │  (Load state from   │
                    │   consent for   │   │   Context Vault)    │
                    │  data use)      │   └──────────┬──────────┘
                    └────────┬────────┘              │
                             │                       │
                    ┌────────▼────────────────────────▼──────┐
                    │           INTENT_DETECTION              │
                    │     (NLU: classify user intent)         │
                    └──┬────────────────────┬────────────┬────┘
                       │                    │            │
            ┌──────────▼────┐    ┌──────────▼──────┐   ┌▼─────────────┐
            │ SLOT_FILLING  │    │  STATUS_QUERY   │   │  ESCALATION  │
            │  (Collect all │    │  (Retrieve app  │   │ (Human handoff│
            │   form fields)│    │   status)       │   │  + RAG summ) │
            └──────┬────────┘    └─────────────────┘   └──────────────┘
                   │
       ┌───────────▼─────────────┐
       │ All required slots      │
       │ filled?                 │
       └───┬───────────┬─────────┘
      No   │           │ Yes
           │           │
  ┌────────▼────┐  ┌───▼──────────────────────────────┐
  │(re-prompt)  │  │        DOCUMENT_CAPTURE          │
  └─────────────┘  │  (Upload + local vision extract) │
                   └──────────────┬───────────────────┘
                                  │
                   ┌──────────────▼───────────────────┐
                   │         DOCUMENT_VERIFY          │
                   │  (Cross-check OCR vs declared)   │
                   └──────────┬──────────┬────────────┘
                    Pass      │          │ Fail/Mismatch
                              │          │
                   ┌──────────▼──┐  ┌────▼──────────────┐
                   │  VALIDATION │  │  CORRECTION_PROMPT │
                   │ (Rules eng) │  │  (Re-collect field)│
                   └──────┬──────┘  └───────────────────┘
                          │
                   ┌──────▼──────┐
                   │  PAYMENT    │
                   │ (Fee calc + │
                   │  UPI/link)  │
                   └──────┬──────┘
                          │
                   ┌──────▼──────┐
                   │  SUBMISSION │
                   │  (Final     │
                   │   record)   │
                   └──────┬──────┘
                          │
                   ┌──────▼──────┐
                   │   OUTCOME   │
                   │  (Receipt + │
                   │  Status)    │
                   └──────┬──────┘
                          │
                   ┌──────▼──────┐
                   │     END     │
                   └─────────────┘
```

### 9.2 Failure Recovery Nodes

| Failure Scenario | Recovery Action | Max Retries |
|---|---|---|
| ASR transcription failure | Re-prompt citizen, offer DTMF fallback | 3 |
| Document upload failure | Re-prompt, offer alternative document type | 2 |
| Payment gateway timeout | Retry after 30s, offer alternative payment method | 3 |
| NLU low confidence (<0.5) | Clarification prompt with explicit options | 2 |
| Validation failure | Specific error message + correction prompt | 5 |
| Session expiry | Restore from PostgreSQL, prompt citizen to confirm | 1 |
| Service adapter failure | Circuit breaker pattern, fallback mock | N/A (failsafe) |

### 9.3 Correction Handling

```python
class CorrectionHandler:
    """
    Handles citizen-initiated corrections to previously filled slots.
    Supports both in-session and cross-session corrections.
    """

    CORRECTION_INTENTS = [
        "correct", "change", "update", "wrong", "mistake",
        "badal", "galat", "theek karo",  # Hindi
        "மாற்று", "திருத்து"              # Tamil
    ]

    def handle_correction(
        self,
        state: ConversationState,
        correction_utterance: str
    ) -> ConversationState:
        # 1. Identify which field is being corrected
        corrected_field = self.identify_correction_target(
            correction_utterance, state.filled_slots
        )

        # 2. Log correction to correction history
        state.correction_history.append({
            "field": corrected_field,
            "old_value": state.filled_slots.get(corrected_field),
            "timestamp": datetime.utcnow().isoformat(),
            "utterance": correction_utterance
        })

        # 3. Clear the corrected slot
        del state.filled_slots[corrected_field]
        state.missing_slots.append(corrected_field)

        # 4. Adjust anomaly score (corrections increase it slightly)
        state.anomaly_score = self.recalculate_anomaly(state)

        # 5. Return to SLOT_FILLING node for this specific field
        state.current_node = "SLOT_FILLING"
        return state
```

---

## 10. Multi-Language & Multi-Modal Strategy

### 10.1 Language Processing Pipeline

```
Input Text (any language)
         │
         ▼
Language Detection
  fastText (local, 176 languages, ~2ms)
  → ISO language code
         │
         ▼
Code-Mix Detection
  Does the text contain multiple scripts? (Hindi + English?)
  → Flag as code-mixed
  → Use IndicBERT or Jugalbandi model for code-mixed NLU
         │
         ▼
Transliteration (if needed)
  Hinglish romanized → Devanagari (e.g., "aay praman patra" → correct interpretation)
  ai4bharat/indic-transliterate (local)
         │
         ▼
Local LLM NLU
  Intent + Entity extraction in any Indian language
  Results are language-neutral structured data
         │
         ▼
Response Generation
  Structured response → prompt template in target language
  Local LLM generates natural language response
         │
         ▼
TTS (if voice channel)
  Piper TTS → audio in citizen's language
```

### 10.2 Prompt Templates — Multilingual

```python
PROMPT_TEMPLATES = {
    "request_name": {
        "hi": "कृपया अपना पूरा नाम बताएं जैसा आधार कार्ड में है।",
        "ta": "தயவுசெய்து ஆதார் அட்டையில் உள்ளதுபோல் உங்கள் முழுப் பெயரை சொல்லுங்கள்.",
        "te": "దయచేసి ఆధార్ కార్డులో ఉన్నట్లుగా మీ పూర్తి పేరు చెప్పండి.",
        "en": "Please tell your full name as it appears on your Aadhaar card.",
        "mr": "कृपया आपले पूर्ण नाव आधार कार्डावर असल्याप्रमाणे सांगा.",
    },
    "correction_confirmation": {
        "hi": "ठीक है। मैंने {field} बदल दिया है। क्या यह सही है: {new_value}?",
        "ta": "சரி. நான் {field} மாற்றியுள்ளேன். இது சரியா: {new_value}?",
        "en": "Okay. I've updated {field}. Is this correct: {new_value}?",
    }
}
```

### 10.3 Dialect & Accent Handling

```
Dialect handling strategy:
1. Whisper is trained on diverse Indian English and Hindi
2. For regional dialects (Bhojpuri, Awadhi, Chhattisgarhi):
   → Use Whisper with language hint "hi" (parent language)
   → Post-processing: common dialect-to-standard word mapping
   → Fallback: offer DTMF if ASR confidence < 0.6

Code-Mixing (e.g., Hinglish):
1. fastText detects mixed script
2. IndicASR (Jugalbandi) handles code-mixed input natively
3. Local LLM handles mixed-language entity extraction naturally

Low-Confidence handling:
→ "Mujhe samajh nahi aaya. Kya aap dobara bata sakte hain?"
  (I didn't understand. Could you please repeat?)
→ If 3 failures: offer explicit options (DTMF menu)
→ If DTMF also fails: escalate to human officer
```

---

## 11. Certificate Services Catalogue (25+ Services)

### 11.1 All Certificate Types (Declarative Spec Coverage)

| # | Certificate | Key Validation Rules | Required Docs | Fee |
|---|---|---|---|---|
| 1 | **Income Certificate** | Income range, annual period | Salary slip / Bank stmt | ₹50 |
| 2 | **Domicile Certificate** | Residence duration ≥ 15 years | Proof of residence, voter ID | ₹50 |
| 3 | **Caste Certificate** | SC/ST/OBC category, lineage | Father's caste cert, school cert | ₹50 |
| 4 | **Nativity Certificate** | Born in state | Birth certificate, school records | ₹50 |
| 5 | **Solvency Certificate** | Property valuation, income | Property documents, income proof | ₹100 |
| 6 | **OBC Certificate** | OBC category, non-creamy layer | Caste proof, income proof | ₹50 |
| 7 | **EWS Certificate** | Income ≤ ₹8 lakh, no other benefits | Income proof, property docs | ₹50 |
| 8 | **Residence Certificate** | Current address proof | Utility bill, voter ID | ₹30 |
| 9 | **Agricultural Land Certificate** | Survey number, patta | Land records | ₹75 |
| 10 | **Minority Certificate** | Religion-based minority | Community proof | ₹50 |
| 11 | **Widow Certificate** | Death certificate of spouse | Marriage cert, death cert | Free |
| 12 | **Single Woman Certificate** | Marital status proof | Affidavit | Free |
| 13 | **Handicap/Disability Cert** | Medical assessment | Medical report | Free |
| 14 | **Senior Citizen Certificate** | Age ≥ 60, address | Age proof | Free |
| 15 | **Birth Certificate** | Birth registration | Hospital records | ₹25 |
| 16 | **Death Certificate** | Death registration | Hospital/cremation records | ₹25 |
| 17 | **Marriage Certificate** | Marriage registration | Witness, photos | ₹100 |
| 18 | **Legal Heir Certificate** | Family tree, succession | Death cert, family tree affidavit | ₹100 |
| 19 | **No Objection Certificate** | Purpose-specific | Application, supporting docs | ₹50 |
| 20 | **Character Certificate** | Police verification | ID proof, photo | ₹50 |
| 21 | **Non-Encumbrance Certificate** | Property clear title | Property documents | ₹200 |
| 22 | **Land Conversion Certificate** | Agricultural to non-agri | Survey, land records | ₹500 |
| 23 | **Patta Transfer Certificate** | Land ownership transfer | Patta, sale deed | ₹300 |
| 24 | **Unemployed Certificate** | Employment status | Affidavit | ₹30 |
| 25 | **Student Certificate** | Enrollment proof | School/college letter | ₹25 |

### 11.2 Config-Driven Architecture — Why It Matters

```
WITHOUT config-driven approach:
  25 services × 200 LOC each = 5,000 LOC of service-specific code
  25 test suites × 50 tests = 1,250 tests to maintain
  Adding certificate #26 = new feature branch + PR + review

WITH config-driven approach:
  25 YAML files × 40 lines each = 1,000 lines of config
  1 test suite × 50 tests = 50 tests (run against all 25 services)
  Adding certificate #26 = create new_cert.yaml file

This is the answer to "Feature Completeness" on the marking scheme
without 25x the engineering effort.
```

---

## 12. Document Intelligence Pipeline

### 12.1 Supported Document Processing

```
DOCUMENT TYPE PROCESSING PIPELINE:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

AADHAAR CARD:
  Input: JPEG/PNG both sides (or single if address is on back)
  Local Model: LayoutLMv3 + custom Aadhaar field detector
  Extracted Fields: name, dob, gender, uid (masked), address, pincode
  Cross-check: uid format (12-digit), name vs conversational data
  Privacy: uid stored encrypted; only checksum used for validation

INCOME PROOF (Salary Slip):
  Input: JPEG/PNG/PDF
  Local Model: LayoutLMv3 + tabular extraction
  Extracted Fields: employer_name, monthly_salary, period, employee_name
  Cross-check: monthly_salary × 12 vs declared annual_income (±20% tolerance)

BANK STATEMENT:
  Input: PDF (multi-page)
  Local Model: DocTR + custom statement parser
  Extracted Fields: account_holder, avg_monthly_balance, period
  Privacy: transaction details never extracted; only aggregate figures

VOTER ID:
  Input: JPEG/PNG both sides
  Local Model: Template-based + LayoutLMv3
  Extracted Fields: name, father_name, dob, epic_number, address

BIRTH CERTIFICATE:
  Input: JPEG/PNG/PDF
  Local Model: LayoutLMv3
  Extracted Fields: name, dob, gender, place_of_birth, registration_number
```

### 12.2 Document Cross-Reference Logic

```python
class DocumentCrossReferencer:
    TOLERANCE_RULES = {
        "annual_income": 0.20,    # 20% variance allowed
        "name": 0.85,             # 85% string similarity (fuzzy match for transliteration differences)
        "dob": 0.00,              # Exact match required
        "address.district": 1.00  # Must match exactly
    }

    def cross_reference(
        self,
        extracted: Dict,
        declared: Dict
    ) -> CrossReferenceResult:
        mismatches = []

        for field, tolerance in self.TOLERANCE_RULES.items():
            if field not in extracted or field not in declared:
                continue

            similarity = self.compute_similarity(
                extracted[field],
                declared[field],
                field_type=self.get_field_type(field)
            )

            if similarity < tolerance:
                mismatches.append(FieldMismatch(
                    field=field,
                    extracted_value=self.mask(extracted[field]),
                    declared_value=self.mask(declared[field]),
                    similarity=similarity,
                    severity=self.get_severity(field, similarity)
                ))

        return CrossReferenceResult(
            mismatches=mismatches,
            passed=len([m for m in mismatches if m.severity == "ERROR"]) == 0
        )
```

---

## 13. Payment & Authentication Architecture

### 13.1 Payment Flow

```
PAYMENT FLOW (UPI-First):
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

1. Fee Calculated → ₹50 for income certificate
2. Payment methods offered (in order of preference):
   a) UPI (Google Pay, PhonePe, BHIM) — QR code or payment link
   b) Debit/Credit Card (via Razorpay/Paytm mock adapter)
   c) Net Banking
   d) Cash at counter (generates a challan for offline payment)

3. Payment Adapter generates payment request:
   → For mock: returns success immediately (test mode)
   → For real: creates Razorpay order, returns checkout URL

4. Payment callback handler (webhook):
   → Verifies HMAC signature of callback
   → Records PaymentTransaction in Data Layer
   → Triggers next state machine step (SUBMISSION)

5. Failure handling:
   → Timeout (30s): Retry prompt
   → Decline: Offer alternative payment method
   → Server error: Circuit breaker, graceful fallback
   → Session expired after payment: Idempotent check (don't double-charge)

IDEMPOTENCY:
  Every payment request has a unique idempotency_key = sha256(application_id + timestamp)
  Payment gateway uses this to prevent duplicate charges on retry
```

### 13.2 Authentication Architecture

```
AUTHENTICATION LAYERS:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

LAYER 1: Channel Identity (Who owns this WhatsApp/phone number?)
  → WhatsApp: Meta-verified phone number
  → IVR: Caller ID from PSTN (validated but not sufficient alone)
  → Web/Mobile: Session token from login

LAYER 2: Citizen Authentication (Is this the actual citizen?)
  → OTP to registered mobile (mock: OTP = "123456")
  → Aadhaar OTP (e-KYC mock via UIDAI sandbox)
  → Biometric (future: fingerprint on kiosk)

LAYER 3: Application-Specific Auth (One-time per application)
  → Consent capture: Explicit "yes" / press 1
  → Application password: Citizen sets during first interaction (optional)
  → DigiLocker integration (mock): Pre-verified documents

AUTH TOKENS:
  → JWT (HS256) for API calls (short-lived: 15 min)
  → Refresh token: stored in HttpOnly cookie (web) or secure storage (mobile)
  → Session token: maps channel identity to citizen_ref (Redis, TTL: 30 min)
```

---

## 14. Observability, Logging & Audit Architecture

### 14.1 Three-Stream Logging Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                    THREE-STREAM LOGGING ARCHITECTURE                │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  STREAM 1: OPERATIONAL LOGS                                         │
│  ─────────────────────────────                                       │
│  What: Service startup, API requests, latency, errors, debug info   │
│  Format: JSON structured logs (no PII)                              │
│  Storage: Loki (7-day retention)                                    │
│  Access: All operations team members                                │
│  Dashboard: Grafana "Operations" dashboard                          │
│                                                                      │
│  STREAM 2: AUDIT LOGS (CRITICAL — separate from ops)               │
│  ───────────────────────────────────────────────────                 │
│  What: Every data access, modification, Data Guard decision,        │
│        consent capture, payment event, submission                   │
│  Format: Immutable append-only JSON (signed with HMAC)             │
│  Storage: OpenSearch (separate index, 7-year retention)             │
│  Access: Audit officers only (separate role)                        │
│  Dashboard: Grafana "Audit & Compliance" dashboard                  │
│  Tamper evidence: Each entry includes HMAC of previous entry        │
│                   (blockchain-like chain of custody)                │
│                                                                      │
│  STREAM 3: METRICS & TRACES                                         │
│  ─────────────────────────────                                       │
│  What: Latency histograms, error rates, throughput, anomaly scores  │
│  Format: Prometheus metrics + OpenTelemetry traces                  │
│  Storage: Prometheus (30-day) + Jaeger (7-day)                     │
│  Access: Operations team                                            │
│  Dashboard: Grafana "Performance" dashboard                         │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘
```

### 14.2 Key Metrics to Expose

```python
# Prometheus metrics definitions
from prometheus_client import Histogram, Counter, Gauge

# Latency metrics
nlu_latency = Histogram(
    "nlu_processing_seconds",
    "Time spent in local LLM NLU",
    buckets=[0.1, 0.25, 0.5, 1.0, 2.0, 5.0]
)
asr_latency = Histogram(
    "asr_processing_seconds",
    "Time spent in local ASR (Whisper)",
    buckets=[0.5, 1.0, 2.0, 5.0, 10.0]
)

# Business metrics
applications_submitted = Counter(
    "applications_submitted_total",
    "Total applications submitted",
    ["service_type", "channel", "language"]
)
data_guard_decisions = Counter(
    "data_guard_decisions_total",
    "Data Guard allow/block decisions",
    ["decision", "caller", "blocked_field"]
)
anomaly_scores = Histogram(
    "anomaly_score",
    "LightGBM fraud/anomaly scores",
    ["service_type"],
    buckets=[0.1, 0.2, 0.4, 0.6, 0.7, 0.8, 0.9, 1.0]
)
active_sessions = Gauge(
    "active_sessions",
    "Currently active citizen sessions",
    ["channel"]
)
```

### 14.3 Audit Log Entry Schema

```python
@dataclass
class AuditEntry:
    entry_id: str               # Unique UUID
    previous_hash: str          # HMAC of previous entry (chain)
    timestamp: datetime         # UTC, microsecond precision
    event_type: AuditEventType  # DATA_ACCESS | DATA_MODIFY | CONSENT |
                                #  PAYMENT | SUBMISSION | DATA_GUARD |
                                #  ESCALATION | AUTH | DOCUMENT_UPLOAD
    actor: str                  # Service name or officer ID
    citizen_ref: str            # Resolved citizen token (never raw PII)
    application_id: Optional[str]
    action: str                 # Verbose description
    outcome: str                # ALLOWED | BLOCKED | SUCCESS | FAILURE
    metadata: Dict              # Event-specific details (NO PII values)
    signature: str              # HMAC-SHA256 of all above fields
```

---

## 15. DevOps, CI/CD & Reproducible Deployment

### 15.1 Repository Layout & Docker Compose

```yaml
# docker-compose.yml — complete one-command setup
version: '3.9'

services:
  # Core Infrastructure
  postgres:
    image: postgres:16-alpine
    volumes:
      - postgres_data:/var/lib/postgresql/data
      - ./data-layer/schema:/docker-entrypoint-initdb.d
    environment:
      POSTGRES_PASSWORD_FILE: /run/secrets/postgres_password
    secrets: [postgres_password]

  redis:
    image: redis:7-alpine
    command: redis-server --requirepass "${REDIS_PASSWORD}" --appendonly yes

  minio:
    image: minio/minio
    command: server /data --console-address ":9001"
    volumes:
      - minio_data:/data
    environment:
      MINIO_ROOT_USER: ${MINIO_ACCESS_KEY}
      MINIO_ROOT_PASSWORD: ${MINIO_SECRET_KEY}

  # AI Services (local, on-prem)
  ollama:
    image: ollama/ollama
    volumes:
      - ollama_models:/root/.ollama
    # Models pulled via healthcheck/init script

  # Policy Engine
  opa:
    image: openpolicyagent/opa:latest
    command: run --server --addr 0.0.0.0:8181 /policies
    volumes:
      - ./data-guard/policies:/policies

  # Application Services
  channel-layer:
    build: ./channel-layer
    depends_on: [redis, orchestration]
    environment:
      ORCHESTRATION_URL: http://orchestration:8001

  orchestration:
    build: ./orchestration
    depends_on: [postgres, redis, ollama, rules-engine]
    environment:
      OLLAMA_URL: http://ollama:11434
      POSTGRES_URL: postgresql://...
      REDIS_URL: redis://...

  rules-engine:
    build: ./rules-engine
    volumes:
      - ./rules-engine/specs:/app/specs  # 25+ YAML service specs

  service-adapters:
    build: ./service-adapters
    depends_on: [postgres, minio, opa]
    environment:
      OPA_URL: http://opa:8181
      MINIO_URL: http://minio:9000

  # Observability
  prometheus:
    image: prom/prometheus
    volumes:
      - ./observability/prometheus.yml:/etc/prometheus/prometheus.yml

  grafana:
    image: grafana/grafana
    volumes:
      - ./observability/grafana/dashboards:/var/lib/grafana/dashboards

  loki:
    image: grafana/loki

  jaeger:
    image: jaegertracing/all-in-one

  opensearch:
    image: opensearchproject/opensearch
    environment:
      discovery.type: single-node
```

### 15.2 CI/CD Pipeline (GitHub Actions)

```yaml
# .github/workflows/ci.yml
name: CI Pipeline

on: [push, pull_request]

jobs:
  lint-and-type-check:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Ruff lint
        run: ruff check .
      - name: MyPy type check
        run: mypy .
      - name: ESLint
        run: cd frontend && npm run lint

  unit-tests:
    runs-on: ubuntu-latest
    steps:
      - name: Run Python unit tests
        run: pytest tests/unit/ -v --cov=. --cov-report=xml
      - name: Coverage threshold
        run: coverage report --fail-under=80

  integration-tests:
    runs-on: ubuntu-latest
    services:
      postgres: {image: postgres:16-alpine}
      redis: {image: redis:7-alpine}
    steps:
      - name: Run integration tests
        run: pytest tests/integration/ -v

  adversarial-pii-tests:
    runs-on: ubuntu-latest
    steps:
      - name: Run Data Guard adversarial tests
        run: pytest tests/adversarial/test_data_guard.py -v
        # MUST PASS: all PII leak attempts must be blocked

  opa-policy-tests:
    runs-on: ubuntu-latest
    steps:
      - name: Run OPA policy tests
        run: opa test data-guard/policies/ -v

  state-machine-tests:
    runs-on: ubuntu-latest
    steps:
      - name: Run conversation flow tests
        run: pytest tests/flows/ -v  # 25+ certificate journey tests
```

### 15.3 Environment Configuration

```
CONFIGURATION SEPARATION:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

.env.example          ← Committed to repo (no secrets, placeholders only)
.env.local            ← Developer local (gitignored)
.env.test             ← Test environment (mock adapters, test DB)
.env.production       ← Production (real adapters, production DB)
secrets/              ← Managed by HashiCorp Vault (never committed)

config/
├── adapters.yaml     ← Which adapter to use per service (mock vs real)
├── models.yaml       ← Which LLM/ASR/TTS model to use
├── features.yaml     ← Feature flags (enable/disable capabilities)
└── channels.yaml     ← Channel configuration (webhook URLs, etc.)

Example adapters.yaml:
  payment:
    adapter: MockPaymentAdapter    # Change to RazorpayAdapter for prod
    config:
      mock_success_threshold: 1000  # Always succeed below this amount

  auth:
    adapter: MockAuthAdapter       # Change to AadhaarOTPAdapter for prod
    config:
      test_otp: "123456"
```

---

## 16. Testing Strategy — Unit, Integration, Adversarial

### 16.1 Testing Pyramid

```
           ┌──────────────────────┐
           │    ADVERSARIAL       │  ← PII leak tests, fuzzing, replay attacks
           │   (10 test cases)    │    MUST BLOCK: all PII leak attempts
           └──────────────────────┘
          ┌────────────────────────┐
          │    INTEGRATION TESTS   │  ← Full journey tests (25 certificate types)
          │   (50 test cases)      │    Including channel switches, corrections
          └────────────────────────┘
         ┌──────────────────────────┐
         │      UNIT TESTS          │  ← Each component tested in isolation
         │   (200+ test cases)      │    All adapters, validators, state machine nodes
         └──────────────────────────┘
```

### 16.2 Adversarial PII Leak Test Suite

```python
# tests/adversarial/test_data_guard.py

class TestDataGuardAdversarial:
    """
    These tests MUST ALL PASS.
    Any failure means PII is leaking to cloud — critical violation.
    """

    def test_raw_aadhaar_blocked(self, data_guard):
        """Direct Aadhaar number in cloud payload must be blocked"""
        payload = {"message": "process this", "aadhaar_number": "1234-5678-9012"}
        with pytest.raises(DataGuardBlockedError) as exc:
            data_guard.check_and_allow(payload, destination="cloud_llm")
        assert "aadhaar_number" in exc.value.blocked_fields

    def test_citizen_name_blocked(self, data_guard):
        """Citizen name in cloud payload must be blocked"""
        payload = {"message": "translate this", "applicant_name": "Ramesh Kumar"}
        with pytest.raises(DataGuardBlockedError):
            data_guard.check_and_allow(payload, destination="cloud_llm")

    def test_nested_pii_blocked(self, data_guard):
        """Nested PII in complex payload must be blocked"""
        payload = {
            "request": {
                "translation": "income certificate",
                "context": {
                    "applicant": {
                        "aadhaar_number": "123456789012"
                    }
                }
            }
        }
        with pytest.raises(DataGuardBlockedError):
            data_guard.check_and_allow(payload, destination="cloud_llm")

    def test_non_sensitive_allowed(self, data_guard):
        """Non-sensitive content should pass through"""
        payload = {"message": "Translate 'income certificate' to Tamil"}
        result = data_guard.check_and_allow(payload, destination="cloud_llm")
        assert result.allowed is True

    def test_synthetic_data_allowed(self, data_guard):
        """Synthetic test data with explicit label should be allowed"""
        payload = {
            "message": "test translation",
            "data_classification": "SYNTHETIC",
            "district": "Test District"  # quasi-identifier
        }
        result = data_guard.check_and_allow(payload, destination="cloud_llm")
        assert result.allowed is True

    def test_pii_removal_from_audio_transcript(self, data_guard):
        """Verify PII is redacted before any cloud call with transcripts"""
        transcript = "My name is Ramesh Kumar and my Aadhaar is 1234-5678-9012"
        redacted = data_guard.redact_transcript(transcript)
        assert "Ramesh Kumar" not in redacted
        assert "1234-5678-9012" not in redacted

    def test_audit_log_created_on_block(self, data_guard, audit_logger):
        """Every block decision must create an audit log entry"""
        payload = {"aadhaar_number": "123456789012"}
        try:
            data_guard.check_and_allow(payload, destination="cloud_llm")
        except DataGuardBlockedError:
            pass
        entries = audit_logger.get_recent(1)
        assert len(entries) == 1
        assert entries[0].outcome == "BLOCKED"
```

### 16.3 Certificate Journey Integration Tests

```python
# tests/integration/test_certificate_journeys.py

@pytest.mark.parametrize("service_type", [
    "INCOME_CERTIFICATE",
    "CASTE_CERTIFICATE",
    "DOMICILE_CERTIFICATE",
    "NATIVITY_CERTIFICATE",
    "SOLVENCY_CERTIFICATE",
    # ... all 25 service types
])
def test_complete_certificate_journey(service_type, client, mock_adapters):
    """Every certificate type must complete a full journey"""
    persona = SyntheticPersona.for_service(service_type)

    # 1. Initiate via WhatsApp
    response = client.post("/channel/whatsapp/webhook", json={
        "from": persona.phone,
        "body": persona.initial_request[service_type],
        "type": "text"
    })
    assert response.status_code == 200

    # 2. Complete slot filling (driven by persona script)
    session = client.get_session(persona.citizen_ref)
    while session.state != "DOCUMENT_CAPTURE":
        slot = session.missing_slots[0]
        client.send_message(persona.citizen_ref, persona.slot_responses[slot])
        session = client.get_session(persona.citizen_ref)

    # 3. Document upload
    doc_path = persona.get_document(service_type)
    client.upload_document(persona.citizen_ref, doc_path)

    # 4. Payment
    client.confirm_payment(persona.citizen_ref)

    # 5. Verify submission
    final_session = client.get_session(persona.citizen_ref)
    assert final_session.state == "OUTCOME"
    assert final_session.payment_status == "PAID"
    assert final_session.filled_slots.get("application_number") is not None


def test_channel_switch_continuity(client, mock_adapters):
    """Citizen starts on WhatsApp, switches to IVR — state must persist"""
    persona = SyntheticPersona.default()

    # Start on WhatsApp
    client.send_whatsapp(persona.phone, "I need an income certificate")
    client.send_whatsapp(persona.phone, persona.name)  # Fill name slot

    session_after_whatsapp = client.get_session(persona.citizen_ref)
    assert "applicant_name" in session_after_whatsapp.filled_slots

    # Switch to IVR — same citizen_ref should be resolved
    client.call_ivr(persona.phone)
    session_after_ivr = client.get_session(persona.citizen_ref)

    # State must be preserved
    assert session_after_ivr.filled_slots == session_after_whatsapp.filled_slots
    assert session_after_ivr.missing_slots == session_after_whatsapp.missing_slots
```

---

## 17. Repository Structure & Code Organization

```
revenue-services-platform/
│
├── README.md                           # Setup, demo instructions, architecture overview
├── docker-compose.yml                  # One-command reproducible setup
├── docker-compose.test.yml             # Test environment
├── .env.example                        # Non-secret config placeholders
├── Makefile                            # Common commands: make setup, make test, make demo
│
├── channel-layer/                      # Channel adapters
│   ├── adapters/
│   │   ├── whatsapp_adapter.py         # Meta/Twilio webhook handler
│   │   ├── ivr_adapter.py              # Asterisk/FreeSWITCH integration
│   │   ├── web_adapter.py              # FastAPI WebSocket handler
│   │   └── mobile_adapter.py          # REST push notification handler
│   ├── asr/
│   │   ├── whisper_asr.py              # faster-whisper integration
│   │   └── indic_asr.py               # IndicASR for regional languages
│   ├── normalizer.py                  # ChannelMessage factory
│   ├── citizen_resolver.py            # citizen_ref resolution
│   └── tests/
│
├── orchestration/                     # Conversation & Orchestration Engine
│   ├── state_machine/
│   │   ├── graph.py                   # LangGraph graph definition
│   │   ├── nodes.py                   # All state machine nodes
│   │   ├── transitions.py             # Transition conditions
│   │   └── state_schema.py            # ConversationState TypedDict
│   ├── agents/
│   │   ├── intake_agent.py            # Slot-filling agent
│   │   ├── validation_agent.py        # Validation + correction agent
│   │   ├── document_agent.py          # Document coordination agent
│   │   ├── payment_agent.py           # Payment flow agent
│   │   ├── escalation_agent.py        # RAG-grounded handoff agent
│   │   └── status_agent.py            # Async status update agent
│   ├── nlu/
│   │   ├── local_llm.py               # Ollama/llama.cpp wrapper
│   │   ├── intent_classifier.py       # Intent detection
│   │   ├── entity_extractor.py        # Entity extraction
│   │   └── pii_tagger.py              # PII identification + tagging
│   ├── context/
│   │   ├── context_vault.py           # Redis + PostgreSQL session store
│   │   └── literacy_analyzer.py       # Literacy level detection
│   ├── dialogue/
│   │   ├── response_generator.py      # Literacy-adaptive responses
│   │   ├── prompt_templates.py        # Multilingual prompt templates
│   │   └── tts_client.py              # Piper TTS wrapper
│   └── tests/
│
├── rules-engine/                      # Business & Rules Engine
│   ├── specs/                         # 25+ YAML service specifications
│   │   ├── income_certificate.yaml
│   │   ├── caste_certificate.yaml
│   │   ├── domicile_certificate.yaml
│   │   ├── nativity_certificate.yaml
│   │   ├── solvency_certificate.yaml
│   │   └── ... (25+ files total)
│   ├── engine.py                      # Declarative rules evaluator
│   ├── validator.py                   # Field-level validation
│   ├── eligibility.py                 # Eligibility condition evaluator
│   ├── fee_calculator.py              # Fee + waiver calculator
│   ├── fraud_scorer.py                # LightGBM anomaly scoring
│   └── tests/
│
├── service-adapters/                  # Service integration adapters
│   ├── interfaces/
│   │   ├── base_adapter.py            # Abstract base class
│   │   ├── auth_adapter.py            # Auth interface
│   │   ├── document_adapter.py        # Document interface
│   │   ├── payment_adapter.py         # Payment interface
│   │   ├── notification_adapter.py    # Notification interface
│   │   └── escalation_adapter.py      # Escalation interface
│   ├── mock/                          # Mock implementations (POC default)
│   │   ├── mock_auth.py
│   │   ├── mock_payment.py
│   │   └── mock_notification.py
│   ├── real/                          # Real implementations (production)
│   │   ├── aadhaar_otp_auth.py
│   │   ├── razorpay_payment.py
│   │   └── sms_notification.py
│   ├── document/
│   │   ├── local_vision.py            # LayoutLMv3 + DocTR integration
│   │   ├── cross_referencer.py        # OCR vs declared data checker
│   │   └── document_types.py         # Supported document type configs
│   ├── rag/
│   │   ├── vector_store.py            # ChromaDB wrapper
│   │   ├── indexer.py                 # Service rulebook indexer
│   │   └── retriever.py               # Similarity search + re-ranking
│   └── tests/
│
├── data-guard/                        # Trust Boundary + Policy Engine
│   ├── policies/
│   │   ├── data_guard_policy.rego     # Main OPA policy
│   │   ├── classification_schema.rego # Data classification rules
│   │   └── tests/
│   │       └── data_guard_test.rego   # OPA policy unit tests
│   ├── middleware.py                  # Data Guard enforcement middleware
│   ├── audit_logger.py               # Immutable audit log writer
│   ├── sanitizer.py                  # PII redaction utilities
│   └── tests/
│       └── test_data_guard.py        # Adversarial PII leak tests
│
├── data-layer/                        # Database schemas and storage config
│   ├── schema/
│   │   ├── 001_init.sql               # Base schema
│   │   ├── 002_audit_tables.sql       # Audit log tables (separate tablespace)
│   │   └── 003_seed_data.sql          # Initial service catalogue, test data
│   ├── models.py                      # SQLAlchemy ORM models
│   ├── repositories/                  # Repository pattern for data access
│   │   ├── application_repo.py
│   │   ├── citizen_repo.py
│   │   ├── document_repo.py
│   │   └── audit_repo.py
│   ├── encryption.py                  # AES-256-GCM field encryption
│   └── minio_client.py               # MinIO object storage wrapper
│
├── models/                           # AI model provider abstraction
│   ├── interfaces/
│   │   ├── llm_interface.py           # Abstract LLM interface
│   │   ├── asr_interface.py           # Abstract ASR interface
│   │   └── tts_interface.py           # Abstract TTS interface
│   ├── local/
│   │   ├── ollama_llm.py              # Ollama implementation
│   │   ├── whisper_asr.py             # faster-whisper implementation
│   │   └── piper_tts.py               # Piper TTS implementation
│   └── cloud/                        # Cloud implementations (Data-Guard gated)
│       ├── anthropic_llm.py           # Claude via Anthropic API
│       └── openai_asr.py              # OpenAI Whisper API (non-sensitive only)
│
├── api-gateway/                       # Kong or Nginx configuration
│   ├── kong.yml                       # Route definitions
│   └── nginx.conf                    # Alternative Nginx config
│
├── frontend/                          # Web portal
│   ├── src/
│   │   ├── app/                       # Next.js 14 app router
│   │   ├── components/               # UI components
│   │   └── lib/                       # API client, utilities
│   └── package.json
│
├── observability/                     # Monitoring configuration
│   ├── prometheus.yml
│   ├── grafana/
│   │   └── dashboards/               # Pre-configured dashboards
│   └── alerts/
│
├── tests/                             # Root test directory
│   ├── unit/                          # Component-level tests
│   ├── integration/                  # Full journey tests
│   ├── adversarial/                  # PII leak, fuzzing tests
│   └── flows/                        # 25+ certificate flow tests
│
├── seed/                              # Test data and synthetic personas
│   ├── personas/                      # Synthetic citizen profiles
│   │   ├── rural_low_literacy.yaml
│   │   ├── urban_professional.yaml
│   │   └── elderly_ivr_user.yaml
│   ├── documents/                    # Sample/mock document images
│   └── scripts/
│       └── seed_db.py                # Database seeding script
│
└── docs/
    ├── adr/                           # Architecture Decision Records
    │   ├── ADR-001-local-llm.md
    │   ├── ADR-002-opa-data-guard.md
    │   ├── ADR-003-langgraph-state-machine.md
    │   └── ADR-004-config-driven-services.md
    └── diagrams/                      # Architecture + sequence diagrams
        ├── system-architecture.drawio
        ├── channel-flow.mmd
        ├── state-machine.mmd
        └── data-guard-sequence.mmd
```

---

## 18. Sequence Diagrams — Key Flows

### 18.1 Channel Switch Continuity Flow

```
Citizen     WhatsApp    Channel   Context    State      IVR
  │          Adapter    Layer     Vault      Machine   Adapter
  │             │         │         │           │         │
  │──voice──►  │         │         │           │         │
  │         ←WhatsApp─►  │         │           │         │
  │            │    normalize      │           │         │
  │            │    ──────────────►│           │         │
  │            │         │   load_session      │         │
  │            │         │    (null)           │         │
  │            │         │   ◄──────────       │         │
  │            │         │                  create       │
  │            │         │   ──────────────────────────► │
  │            │         │   ◄────session_created────── │
  │            │         │   save_session               │
  │            │         │────────────────────────►      │
  │            │         │                              │
  │  [fills some slots via WhatsApp...]                 │
  │                                                     │
  │──dials─────────────────────────────────────────────►│
  │                                                     │resolve
  │                                                     │citizen_ref
  │                                                     │────────────►│
  │                                                     │◄────────────│
  │                                                     │load_session │
  │                                                     │(has slots)  │
  │                                                     │────────────►│
  │                                                     │◄────────────│
  │  "Welcome back. Continuing your income certificate application..." │
  │◄────────────────────────────────────────────────────│
```

### 18.2 Data Guard Block Demo Flow

```
Orchestration   Data Guard    OPA Engine    Audit Logger   Cloud LLM
Engine            Middleware      (Rego)                      (blocked)
   │                 │               │           │               │
   │──outbound_call──►               │           │               │
   │                 │               │           │               │
   │                 │──evaluate──►  │           │               │
   │                 │  {payload,    │           │               │
   │                 │   policy}     │           │               │
   │                 │               │           │               │
   │                 │  ◄──result──  │           │               │
   │                 │  {allow:false,│           │               │
   │                 │   blocked:    │           │               │
   │                 │   [aadhaar]}  │           │               │
   │                 │               │           │               │
   │                 │──audit_entry──────────────►               │
   │                 │               │           │               │
   │◄──BLOCK_ERROR── │               │           │               │
   │  (never reaches)│               │           │         (never called)
   │                 │               │           │               │
   │──local_llm─────────────────────────────────────────────────►
   │  (fallback)     │               │           │         [Local LLM]
```

---

## 19. Synthetic Personas & Test Data Strategy

### 19.1 Three Core Personas

```yaml
# seed/personas/rural_low_literacy.yaml
persona:
  id: "P001"
  name: "Ramesh Kumar"   # Only used locally in seed data
  profile:
    literacy_level: LOW
    language: "hi"
    preferred_channel: IVR
    has_smartphone: false
    agent_assisted: true   # Village agent helps them
  behavior:
    utterance_style: "very_short"
    correction_frequency: HIGH
    dtmf_preference: true
    code_mixing: false
  use_case: "Widow certificate for pension eligibility"
  journey_script:
    - input: "praman patra chahiye" # (Need a certificate)
      expected_intent: CERTIFICATE_REQUEST
    - input: "1"   # DTMF for widow certificate
      expected_intent: WIDOW_CERTIFICATE_SELECT
    # ... full script

# seed/personas/urban_professional.yaml
persona:
  id: "P002"
  name: "Priya Sharma"
  profile:
    literacy_level: HIGH
    language: "en"
    preferred_channel: WEB
    has_smartphone: true
  behavior:
    utterance_style: "verbose"
    correction_frequency: LOW
  use_case: "Income certificate for job application"
  journey_script:
    - input: "I need an income certificate for my job application"
      expected_intent: INCOME_CERTIFICATE
    # ... full script

# seed/personas/elderly_ivr_user.yaml
persona:
  id: "P003"
  language: "ta"  # Tamil
  profile:
    literacy_level: MEDIUM
    preferred_channel: IVR
    preferred_dtmf: true
  use_case: "Senior citizen certificate"
  negative_test_cases:
    - description: "Income exceeds limit for free certificate"
      input_income: 500000  # > waiver threshold
      expected_waiver: false
      expected_fee: 50
```

### 19.2 Negative Test Cases

```python
NEGATIVE_TEST_CASES = [
    # Eligibility failures
    {"name": "underage_applicant", "dob_years_ago": 15,
     "expected_error": "Applicant must be 18 or older"},
    
    # Document mismatches
    {"name": "income_mismatch", "declared_income": 100000, "doc_income": 200000,
     "expected_outcome": "MANUAL_REVIEW"},
    
    # Fraud attempts
    {"name": "rapid_resubmission", "resubmit_count": 5, "time_window_minutes": 10,
     "expected_anomaly_score": 0.85, "expected_outcome": "REJECT"},
    
    # PII leak attempts (must be blocked)
    {"name": "aadhaar_in_cloud_payload", "payload": {"aadhaar": "123456789012"},
     "destination": "cloud_llm", "expected_outcome": "DATA_GUARD_BLOCK"},
    
    # Payment failures
    {"name": "payment_declined", "payment_response": "DECLINED",
     "expected_next_state": "PAYMENT_RETRY"},
    
    # Session expiry
    {"name": "session_expired", "session_age_minutes": 45,
     "expected_outcome": "SESSION_RESTORED_FROM_DB"},
    
    # Invalid format inputs
    {"name": "invalid_aadhaar", "aadhaar": "12345",
     "expected_error": "Aadhaar must be 12 digits"},
    
    # Unsupported language (graceful fallback)
    {"name": "unsupported_dialect", "language": "bho",  # Bhojpuri
     "expected_fallback_language": "hi"},
]
```

---

## 20. Enterprise-Level Enhancements & Differentiators

### 20.1 Differentiators vs. Typical POC

| Typical POC | This Platform |
|---|---|
| Single certificate type | Config-driven engine covers all 25+ services |
| Chatbot that forgets context on channel switch | Context Vault: channel-agnostic session state |
| Cloud OCR for documents (PII leak risk) | Local LayoutLMv3: zero cloud document exposure |
| Data Guard as a diagram box | Data Guard as live OPA/Rego runtime that can block calls in demo |
| Simple intent matching | Multi-agent LangGraph with 6 specialized agents |
| Basic TTS/ASR | Local Whisper + Piper: 7+ Indian languages, offline-capable |
| No fraud detection | LightGBM anomaly scoring with SHAP explainability |
| Single operational log stream | Three-stream architecture: ops + audit (tamper-evident) + metrics |
| Translation only for multilingual | Literacy-adaptive, code-mix-aware dialogue system |
| Mock adapters without interfaces | Full adapter pattern: mock = real, swappable via config |

### 20.2 Enterprise Scalability Path

```
POC (Hackathon) → Pilot (District) → State → National Scale

POC:
  Single Docker Compose
  1 node, all services co-located
  Ollama CPU-only (Llama 8B)
  Mock adapters for payments, auth, certificates
  
Pilot (1 District, ~10K applications/day):
  Docker Compose → k3s Kubernetes (lightweight)
  Separate Ollama node with GPU
  Real payment adapter (Razorpay)
  Real auth adapter (Aadhaar OTP)
  PostgreSQL with streaming replication
  
State (100 Districts, ~1M applications/day):
  Kubernetes cluster (on-prem)
  vLLM for high-throughput LLM inference
  PostgreSQL → Citus distributed DB
  Redis Cluster for session management
  Separate ML cluster for LightGBM retraining
  
National Scale:
  Multi-region on-prem (state data centers)
  Each state = independent trust zone
  Central audit aggregation only (non-PII metrics)
  Federated learning for fraud model updates
```

### 20.3 Accessibility Enhancements

```
DIGITAL ACCESSIBILITY FEATURES:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

1. DTMF-FIRST IVR:
   - Complete service journey possible via DTMF alone
   - Voice input optional, always falls back to DTMF
   - Audio prompts repeated automatically after silence timeout

2. SLOW-READER ADAPTATION:
   - Response audio speed adjustable (0.8x for elderly)
   - Shorter sentences for LOW literacy profiles
   - Confirmation after every data point captured

3. ASSISTED MODE:
   - Village-level entrepreneur (CSC center) can assist citizen
   - Operator view: same state machine, additional admin controls
   - Consent from citizen explicitly captured even in assisted mode

4. OFFLINE-CAPABLE KIOSK:
   - All AI models local → works without internet
   - Documents scanned locally → queued for processing
   - Payment: challan generation works offline, collected later

5. SCREEN-READER COMPATIBILITY:
   - WCAG 2.1 AA compliance for web portal
   - Semantic HTML, ARIA labels, keyboard navigation
   - High-contrast mode toggle

6. VISUAL IMPAIRMENT:
   - Complete voice-only journey supported
   - Text responses also sent as WhatsApp messages
   - Receipt available as audio summary
```

### 20.4 Operational Excellence Features

```
OPERATIONAL EXCELLENCE:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

1. CIRCUIT BREAKER PATTERN:
   Every adapter has circuit breaker (Tenacity/PyBreaker):
   - Closed: normal operation
   - Open: adapter failed 3x in 5min → instant mock fallback
   - Half-open: probe real adapter every 30s

2. GRACEFUL DEGRADATION:
   - NLU unavailable → keyword-based intent matching
   - Document adapter unavailable → manual document review flag
   - Payment gateway down → challan generation + offline payment
   - TTS unavailable → text-only response

3. HEALTH ENDPOINTS:
   Every service exposes /health endpoint:
   {
     "status": "healthy",
     "components": {
       "ollama": "up",
       "postgres": "up",
       "redis": "up",
       "opa": "up"
     },
     "latency_p99_ms": 850
   }

4. RATE LIMITING:
   - Per citizen_ref: 100 requests/hour (anti-bot)
   - Per channel: 1000 requests/minute (DDoS protection)
   - Per service type: configurable (high-demand services)

5. DATA RETENTION POLICIES:
   - Conversation audio: 7 days (then purged, logged)
   - Application data: 7 years (per government retention rules)
   - Audit logs: permanent (immutable)
   - Session cache: 30-minute TTL with DB fallback
```

---

## 21. Scoring Alignment Matrix

> This section maps every feature to the marking scheme criteria to ensure full coverage.

### 21.1 Enterprise Architecture & Data Isolation (4/10)

| Requirement | Implementation | Evidence |
|---|---|---|
| Restricted data stays local | Data Guard (OPA/Rego) blocks all cloud calls with PII | Live demo: block + audit entry |
| Mock identity data not to cloud | citizen_ref tokens used everywhere; raw IDs never transmitted | Adversarial test suite: all pass |
| Approved non-sensitive content to cloud | Data Guard allows only non-sensitive; tested in CI | OPA policy tests |
| Enforced adapters (not just logging) | DataGuardBlockedError raised + logged at runtime | Live block demo |
| On-premise ready architecture | All services in Docker Compose; Kubernetes configs included | `docker-compose up` reproducible |

### 21.2 Feature Completeness (4/10)

| Feature Category | Implementation | Coverage |
|---|---|---|
| **Voice** | Local Whisper ASR → NLU → Piper TTS | WhatsApp voice notes + IVR |
| **Languages** | 7+ Indian languages + code-mix | Prompt templates in all languages |
| **Forms** | Slot-filling state machine + validation | All 25+ service YAML specs |
| **Document processing** | Local LayoutLMv3 extraction + cross-reference | All major government doc types |
| **Authentication** | OTP + mock DigiLocker + consent capture | Mock adapter + real interface |
| **Payment** | Mock UPI + real adapter interface | Razorpay adapter ready |
| **Channel** | WhatsApp + IVR + Web + Mobile | 4 adapters with common interface |
| **Status** | Status Agent + proactive push | Any channel, any language |
| **Analytics** | Grafana dashboard + Prometheus | Live metrics during demo |
| **Accessibility** | DTMF-first, literacy-adaptive, assisted mode | Persona-based test scripts |
| **Escalation** | RAG-grounded handoff + ticket creation | Escalation adapter + demo script |

### 21.3 Code Quality & Technical Execution (2/10)

| Requirement | Implementation |
|---|---|
| Conversation state machine | LangGraph with full state diagram + transitions |
| Adapter-based integrations | Abstract interfaces + mock + real implementations |
| Failure recovery | Circuit breaker + retry logic + graceful degradation |
| Automated tests | 200+ unit, 50+ integration, 10+ adversarial |
| Observability | Prometheus + Grafana + Loki + Jaeger + OpenTelemetry |
| Configuration separation | YAML configs + .env files + HashiCorp Vault |
| Reproducible deployment | `docker-compose up` + Makefile + seed scripts |
| Static analysis | Ruff + mypy + ESLint pre-commit hooks |
| Secrets exclusion | git-secrets + detect-secrets in CI |
| Architecture decision records | 4+ ADRs in /docs/adr/ |

---

## 22. Implementation Roadmap

### Phase 1: Foundation (Hours 0–4)
```
✅ Set up Docker Compose with PostgreSQL, Redis, MinIO, OPA
✅ Implement Data Guard middleware with OPA policy
✅ Create ChannelMessage schema and basic WhatsApp adapter
✅ Set up LangGraph state machine skeleton
✅ Create income_certificate.yaml (first service spec)
✅ Write first adversarial PII test (must pass before anything else)
```

### Phase 2: Core Journey (Hours 4–12)
```
✅ Integrate Ollama + Llama 3.1 8B for local NLU
✅ Implement slot-filling agent (Intake Agent)
✅ Implement Context Vault (Redis + PostgreSQL)
✅ Implement Business Rules Engine (reads YAML specs)
✅ Implement Mock Auth, Document, Payment adapters
✅ Complete income certificate end-to-end journey
✅ Write integration test for complete income cert journey
```

### Phase 3: AI & Multilingual (Hours 12–20)
```
✅ Integrate faster-whisper for IVR ASR
✅ Integrate Piper TTS for voice responses
✅ Add IVR adapter
✅ Implement language detection + multilingual templates
✅ Implement literacy-adaptive dialogue
✅ Integrate LayoutLMv3 for local document OCR
✅ Implement document cross-reference check
```

### Phase 4: All 25 Services + Fraud (Hours 20–28)
```
✅ Create YAML specs for remaining 24 certificate types
✅ Train/load LightGBM anomaly scorer on synthetic data
✅ Implement escalation adapter with RAG (ChromaDB)
✅ Implement status agent (async proactive push)
✅ Add channel switch continuity demo (WhatsApp → IVR)
✅ Implement correction handling
```

### Phase 5: Observability & Polish (Hours 28–36)
```
✅ Grafana dashboards (operations + audit + anomaly)
✅ Prometheus metrics for all key components
✅ Audit log three-stream architecture
✅ Web portal (Next.js)
✅ Full adversarial test suite (all must pass)
✅ Demo narrative script finalized
✅ Seed synthetic personas and test data
✅ README + Architecture diagrams + ADRs
```

---

## 23. Architecture Decision Records (ADRs)

### ADR-001: Local LLM over Cloud LLM for NLU

**Status:** Accepted

**Context:** The NLU component processes all citizen utterances, which contain PII (names, IDs, financial data, addresses). A cloud LLM would expose this data to third-party servers.

**Decision:** Use local quantized LLM (Llama 3.1 8B Q4_K_M via Ollama) as the primary NLU model. Cloud LLM (Claude/GPT) used only for non-sensitive tasks (language polishing of generic strings), gated through Data Guard.

**Consequences:**
- ✅ Zero PII exposure via NLU
- ✅ Works offline / on-premise
- ⚠️ Higher hardware requirements (8GB RAM minimum for 8B model)
- ⚠️ Slightly lower NLU quality for complex queries vs. frontier cloud models
- Mitigation: Use keyword fallback for very low-confidence NLU results

---

### ADR-002: OPA/Rego for Data Guard over Custom Code

**Status:** Accepted

**Context:** The Data Guard must enforce data classification policies reliably and auditly. A custom-coded data guard might miss edge cases or be hard to audit.

**Decision:** Use Open Policy Agent (OPA) with Rego policy language. Policies are declarative, separately testable, and industry-standard.

**Consequences:**
- ✅ Policy is auditable and human-readable
- ✅ OPA tests are independent of application code
- ✅ Industry-recognized standard for policy enforcement
- ⚠️ Learning curve for Rego language
- ⚠️ Additional service to maintain (OPA sidecar/server)

---

### ADR-003: LangGraph for State Machine over Custom FSM

**Status:** Accepted

**Context:** The conversation state machine has 12+ states, complex transitions, and multi-agent coordination requirements. A hand-rolled FSM would be brittle.

**Decision:** Use LangGraph (LangChain's agent framework) for the state machine. It natively supports graph-based state management, multi-agent coordination, and state persistence.

**Consequences:**
- ✅ Graph-based state management with built-in persistence
- ✅ Native multi-agent support (supervisor pattern)
- ✅ Checkpointing for session recovery
- ⚠️ Dependency on LangChain ecosystem
- Mitigation: State schema is pure Python dataclass — could be ported to another framework if needed

---

### ADR-004: Config-Driven Rules Engine over Service-Specific Code

**Status:** Accepted

**Context:** The platform must support 25+ certificate types, each with unique rules. Implementing each as separate code would be unmaintainable and would fail the "Feature Completeness" criterion.

**Decision:** All service definitions are declarative YAML files consumed by a single generic rules engine. Adding a new service = creating a YAML file, not writing new code.

**Consequences:**
- ✅ 25+ services covered with single rules engine
- ✅ Non-developers can author new service specs
- ✅ Service specs can be validated independently
- ⚠️ YAML schema must be comprehensive enough to capture all rule types
- ⚠️ Complex cross-field validations may need escaping to Python expressions

---

> **Document Version:** 1.0  
> **Last Updated:** 2026-08-19  
> **Prepared for:** AI Club Hackathon — Multilingual Voice-First Revenue Services Platform  
> **Aligned to:** Problem statement in `first.md` and assessment marking scheme (4+4+2 = 10/10)

---

*This document covers every component, every flow, every tech choice with justification, every security measure, and every scoring criterion. Build from Phase 1 in the roadmap and you will have a provably enterprise-grade, marks-maximizing solution.*
