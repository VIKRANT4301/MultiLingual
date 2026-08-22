# Setup Instructions

Follow these steps to run the platform locally.

## Prerequisites
- Python 3.11+
- Node.js 18+ & npm
- Windows Powershell or standard terminal

---

## 1. Backend Setup

1. Navigate to the `backend/` directory:
   ```bash
   cd backend
   ```
2. Create and activate a Python virtual environment:
   ```bash
   python -m venv venv
   .\venv\Scripts\activate
   ```
3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
4. Copy the environment template and verify settings:
   ```bash
   cp .env.example .env
   ```
5. Start the FastAPI backend:
   ```bash
   python -m uvicorn main:app --reload --port 8000
   ```
The backend server will run on [http://localhost:8000](http://localhost:8000) and dynamically seed the database on startup.

---

## 2. Frontend Setup

1. Navigate to the `frontend/` directory:
   ```bash
   cd frontend
   ```
2. Install dependencies:
   ```bash
   npm install
   ```
3. Run the development server (configured for Web platform):
   ```bash
   npm run web
   ```
The browser will automatically open [http://localhost:19006](http://localhost:19006) displaying the government-service portal interface.

---

## 3. Running Automated Tests

To verify that the state transitions, data guard filters, and E2E journeys are functional:
```bash
cd backend
python -m pytest
```
