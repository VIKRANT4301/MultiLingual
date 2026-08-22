from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
from datetime import datetime

# Token Schemas
class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    username: Optional[str] = None
    role: Optional[str] = None

# User Schemas
class UserCreate(BaseModel):
    username: str
    password: str
    role: str = "CITIZEN"

class UserLogin(BaseModel):
    username: str
    password: str

class UserOut(BaseModel):
    id: int
    username: str
    role: str
    created_at: datetime

    class Config:
        from_attributes = True

# Citizen Schemas
class CitizenOut(BaseModel):
    id: int
    full_name: Optional[str] = None
    phone_number: Optional[str] = None
    email: Optional[str] = None
    address: Optional[str] = None
    preferred_language: str

    class Config:
        from_attributes = True

# Service Schemas
class ServiceOut(BaseModel):
    id: str
    name: str
    description: Optional[str] = None
    required_documents: List[str]
    fee: float
    processing_days: int

    class Config:
        from_attributes = True

# Document Schemas
class DocumentOut(BaseModel):
    id: int
    doc_type: str
    file_name: str
    file_path: str
    status: str
    verification_result: Optional[str] = None
    version: int
    is_latest: bool
    created_at: datetime

    class Config:
        from_attributes = True

class DocumentVersionOut(BaseModel):
    id: int
    version: int
    file_name: str
    status: str
    verification_result: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True

class DocumentDetailOut(BaseModel):
    doc_type: str
    latest_version: DocumentOut
    versions: List[DocumentVersionOut]

class BulkUploadJobOut(BaseModel):
    id: str
    application_id: int
    total_files: int
    processed_files: int
    failed_files: int
    status: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

class DocumentExtractionOut(BaseModel):
    id: int
    document_id: int
    extracted_data: Dict[str, Any]
    confidence_score: float
    status: str
    error_message: Optional[str] = None

    class Config:
        from_attributes = True

# Payment Schemas
class PaymentInitiate(BaseModel):
    application_id: int
    payment_method: str # UPI, Card, Net Banking
    amount: float

class PaymentConfirm(BaseModel):
    status: str # SUCCESS, FAILED
    transaction_no: Optional[str] = None
    error_message: Optional[str] = None

class PaymentOut(BaseModel):
    id: int
    application_id: int
    amount: float
    payment_method: str
    status: str
    transaction_no: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True

# Application Schemas
class ApplicationOut(BaseModel):
    id: int
    application_no: str
    citizen_id: Optional[int] = None
    service_id: str
    status: str
    language: str
    channel: str
    created_at: datetime
    updated_at: datetime
    
    citizen: Optional[CitizenOut] = None
    service: ServiceOut

    class Config:
        from_attributes = True

# Conversation Schemas
class MessageRequest(BaseModel):
    session_id: str
    text: Optional[str] = ""
    channel: str = "Web" # Web, Voice, WhatsApp, IVR
    language: Optional[str] = None # Force a language if selected in UI

class MessageResponse(BaseModel):
    session_id: str
    text: str
    state: str
    language: str
    intent: Optional[str] = None
    extracted_data: Dict[str, Any] = {}
    missing_fields: List[str] = []
    application_id: Optional[int] = None
    audio_data: Optional[str] = None # Base64 audio if TTS processed on server (we'll mostly do browser TTS)
    is_blocked: bool = False
    block_reason: Optional[str] = None
    redirect_to_service: Optional[str] = None

# Correction & Escalation Schemas
class CorrectionRequest(BaseModel):
    field_name: str
    new_value: str
    reason: str

class EscalationOut(BaseModel):
    id: int
    application_id: int
    case_id: str
    reason: str
    status: str
    priority: str
    conversation_context: Optional[str] = None
    failed_steps: List[str]
    documents_status: List[Any]
    created_at: datetime

    class Config:
        from_attributes = True

# Audit Log Schemas
class AuditLogOut(BaseModel):
    id: int
    timestamp: datetime
    actor: str
    action: str
    application_id: Optional[int] = None
    channel: Optional[str] = None
    result: Optional[str] = None
    metadata_json: Dict[str, Any]

    class Config:
        from_attributes = True

# Dashboard Metrics Schemas
class DashboardMetrics(BaseModel):
    total_applications: int
    applications_today: int
    completed_applications: int
    pending_applications: int
    failed_applications: int
    escalations: int
    avg_processing_time_hours: float
    avg_response_latency_ms: float
    payment_success_rate: float
    doc_validation_success_rate: float

class DashboardChartData(BaseModel):
    services: Dict[str, int]
    languages: Dict[str, int]
    channels: Dict[str, int]
    statuses: Dict[str, int]
    blocked_requests: int
