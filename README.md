# Multilingual Voice-First Revenue Services Platform — POC

This is a complete, runnable Proof of Concept (POC) demonstrating how a citizen can request and complete a government Revenue Department certificate service through natural voice and text conversation in regional languages instead of navigating complex digital portals.

> **IMPORTANT NOTE**: This is a POC/Prototype environment. Authentication (OTP), payments, government API checks, and certificate PDF generation are fully mocked for demo purposes. `POC_MODE=true` is enabled by default.

---

## Key Features

1. **Voice-First Interaction**: Allows text input and voice interaction to request revenue services.
2. **Income Certificate E2E Journey**: Complete conversational flow:
   - Greeting & Language Selection (English, Hindi, Marathi)
   - Dynamic service matching
   - Consent management
   - Conversational form details capture (Name, District, Annual Income)
   - Data and rule validation (e.g. maximum income thresholds)
   - Document upload and mock OCR comparison/mismatch correction
   - Aadhaar OTP authentication mock
   - Fee calculation (₹50) & mock UPI payment
   - Submission, application tracking, and PDF certificate generation
3. **Configuration-Driven Service Catalogue**: Services (25 in total) are dynamically mapped via SQLite. Key configurations are parsed from YAML files under the `services/` directory.
4. **Sovereignty DLP (Data Guard)**: Local regex-based PII filter flags and blocks Aadhaar, emails, or phone numbers from being sent to external/cloud LLM providers.
5. **Omnichannel Simulator**: Unified layout featuring Web Portal interface, WhatsApp chat bubble, and an IVR phone call simulator.
6. **Operations Dashboard**: Admin KPI metrics, manual verification queue, and Sovereignty Guard audit logs.

---

## Tech Stack

* **Backend**: FastAPI, SQLAlchemy, SQLite, PyYAML, Pytest
* **Frontend**: Expo React Native (configured for Web build)

---

## Directory Structure

```text
MultiLingual/
├── backend/
│   ├── app/
│   │   ├── api/          # Endpoints (auth, conversation, applications, dashboard)
│   │   ├── models/       # SQLAlchemy models
│   │   ├── services/     # State machine, DLP DataGuard, OPA policy engine
│   │   └── core/         # Core config & Database connections
│   ├── tests/            # Automated Pytest suite
│   ├── main.py           # Startup, database initialization, and seeding
│   └── requirements.txt
├── services/             # Dynamic YAML configurations
├── data/locales/         # Localization files (en, hi, mr)
├── docs/                 # Architecture, API, Setup, and Demo Script docs
└── README.md
```

---

## Getting Started

Refer to [`docs/setup.md`](file:///c:/Users/ABHAY%20SATHAWANE/Project/MultiLingual/docs/setup.md) for full backend and frontend setup and running instructions.

---

## Automated Tests

To execute the test suite, run:

```bash
cd backend
python -m pytest
```
