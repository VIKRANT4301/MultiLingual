import datetime
from sqlalchemy import (
    Column, Integer, String, ForeignKey, DateTime, 
    Boolean, Text, JSON, Float, Numeric
)
from sqlalchemy.orm import relationship
from backend.app.core.database import Base

class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    role = Column(String, default="CITIZEN")  # CITIZEN, OFFICER, ADMIN, AUDITOR
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    
    citizen = relationship("Citizen", back_populates="user", uselist=False)

class Citizen(Base):
    __tablename__ = "citizens"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    full_name = Column(String, nullable=True)
    aadhaar_hash = Column(String, nullable=True) # hashed/encrypted locally
    phone_number = Column(String, nullable=True)
    email = Column(String, nullable=True)
    address = Column(Text, nullable=True)
    preferred_language = Column(String, default="en") # en, hi, mr
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    
    user = relationship("User", back_populates="citizen")

class Service(Base):
    __tablename__ = "services"
    
    id = Column(String, primary_key=True, index=True) # e.g. "income_certificate"
    name = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    required_documents = Column(JSON, nullable=False) # list of string types
    fee = Column(Float, default=0.0)
    processing_days = Column(Integer, default=7)

class Application(Base):
    __tablename__ = "applications"
    
    id = Column(Integer, primary_key=True, index=True)
    application_no = Column(String, unique=True, index=True, nullable=False) # INC-2026-XXXXXX
    citizen_id = Column(Integer, ForeignKey("citizens.id"), nullable=True)
    service_id = Column(String, ForeignKey("services.id"), nullable=False)
    status = Column(String, default="SUBMITTED") # SUBMITTED, UNDER_REVIEW, APPROVED, REJECTED, etc.
    language = Column(String, default="en")
    channel = Column(String, default="Web") # Web, Voice, WhatsApp, IVR, Mobile
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)
    
    citizen = relationship("Citizen")
    service = relationship("Service")
    documents = relationship("Document", back_populates="application")
    payments = relationship("Payment", back_populates="application")
    escalations = relationship("Escalation", back_populates="application")
    states = relationship("ApplicationState", back_populates="application", uselist=False)

class ApplicationState(Base):
    __tablename__ = "application_states"
    
    id = Column(Integer, primary_key=True, index=True)
    application_id = Column(Integer, ForeignKey("applications.id"), nullable=False)
    current_state = Column(String, default="START")
    state_data = Column(JSON, default=dict) # stores gathered data
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)
    
    application = relationship("Application", back_populates="states")

class Document(Base):
    __tablename__ = "documents"
    
    id = Column(Integer, primary_key=True, index=True)
    application_id = Column(Integer, ForeignKey("applications.id"), nullable=False)
    doc_type = Column(String, nullable=False) # identity_proof, income_proof, etc.
    file_name = Column(String, nullable=False)
    file_path = Column(String, nullable=False)
    status = Column(String, default="PENDING") # PENDING, VALIDATED, FAILED, REVIEW_REQUIRED
    verification_result = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    
    application = relationship("Application", back_populates="documents")
    extraction = relationship("DocumentExtraction", back_populates="document", uselist=False)

class DocumentExtraction(Base):
    __tablename__ = "document_extractions"
    
    id = Column(Integer, primary_key=True, index=True)
    document_id = Column(Integer, ForeignKey("documents.id"), nullable=False)
    extracted_data = Column(JSON, default=dict)
    confidence_score = Column(Float, default=1.0)
    status = Column(String, default="SUCCESS") # SUCCESS, FAILED
    error_message = Column(String, nullable=True)
    
    document = relationship("Document", back_populates="extraction")

class Payment(Base):
    __tablename__ = "payments"
    
    id = Column(Integer, primary_key=True, index=True)
    application_id = Column(Integer, ForeignKey("applications.id"), nullable=False)
    amount = Column(Float, nullable=False)
    payment_method = Column(String, nullable=False) # UPI, Card, Net Banking
    status = Column(String, default="INITIATED") # INITIATED, SUCCESS, FAILED, TIMEOUT, CANCELLED
    transaction_no = Column(String, unique=True, index=True, nullable=True)
    error_message = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)
    
    application = relationship("Application", back_populates="payments")

class AuthenticationAttempt(Base):
    __tablename__ = "authentication_attempts"
    
    id = Column(Integer, primary_key=True, index=True)
    application_id = Column(Integer, ForeignKey("applications.id"), nullable=True)
    auth_type = Column(String, nullable=False) # AADHAAR, OTP
    identifier = Column(String, nullable=False) # masked Aadhaar or phone
    success = Column(Boolean, default=False)
    error_message = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

class Conversation(Base):
    __tablename__ = "conversations"
    
    id = Column(String, primary_key=True, index=True) # sessionId
    application_id = Column(Integer, ForeignKey("applications.id"), nullable=True)
    citizen_id = Column(Integer, ForeignKey("citizens.id"), nullable=True)
    channel = Column(String, default="Web") # Web, Voice, WhatsApp, IVR
    language = Column(String, default="en")
    active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    
    messages = relationship("ConversationMessage", back_populates="conversation")

class ConversationMessage(Base):
    __tablename__ = "messages"
    
    id = Column(Integer, primary_key=True, index=True)
    conversation_id = Column(String, ForeignKey("conversations.id"), nullable=False)
    role = Column(String, nullable=False) # user, assistant, system
    content = Column(Text, nullable=False)
    audio_path = Column(String, nullable=True)
    classification = Column(String, default="PUBLIC") # PUBLIC, RESTRICTED, etc.
    timestamp = Column(DateTime, default=datetime.datetime.utcnow)
    
    conversation = relationship("Conversation", back_populates="messages")

class Escalation(Base):
    __tablename__ = "escalations"
    
    id = Column(Integer, primary_key=True, index=True)
    application_id = Column(Integer, ForeignKey("applications.id"), nullable=False)
    case_id = Column(String, unique=True, index=True, nullable=False)
    reason = Column(Text, nullable=False)
    status = Column(String, default="PENDING") # PENDING, RESOLVED
    assigned_to_officer_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    conversation_context = Column(Text, nullable=True)
    failed_steps = Column(JSON, default=list)
    documents_status = Column(JSON, default=list)
    priority = Column(String, default="HIGH") # LOW, MEDIUM, HIGH
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)
    
    application = relationship("Application", back_populates="escalations")

class AuditLog(Base):
    __tablename__ = "audit_logs"
    
    id = Column(Integer, primary_key=True, index=True)
    timestamp = Column(DateTime, default=datetime.datetime.utcnow)
    actor = Column(String, nullable=False) # system, citizen_id, user_id
    action = Column(String, nullable=False) # APPLICATION_CREATED, PAYMENT_SUCCESS, etc.
    application_id = Column(Integer, nullable=True)
    channel = Column(String, nullable=True)
    result = Column(String, nullable=True) # SUCCESS, BLOCKED, FAILED
    metadata_json = Column(JSON, default=dict)

class Notification(Base):
    __tablename__ = "notifications"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    application_id = Column(Integer, ForeignKey("applications.id"), nullable=True)
    title = Column(String, nullable=False)
    message = Column(Text, nullable=False)
    read = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

class Certificate(Base):
    __tablename__ = "certificates"
    
    id = Column(Integer, primary_key=True, index=True)
    application_id = Column(Integer, ForeignKey("applications.id"), nullable=False)
    certificate_no = Column(String, unique=True, index=True, nullable=False)
    file_path = Column(String, nullable=False)
    issue_date = Column(DateTime, default=datetime.datetime.utcnow)
    expiry_date = Column(DateTime, nullable=True)
    qr_code_data = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

class ServiceRule(Base):
    __tablename__ = "service_rules"
    
    id = Column(Integer, primary_key=True, index=True)
    service_id = Column(String, ForeignKey("services.id"), nullable=False)
    rule_name = Column(String, nullable=False)
    rule_condition = Column(String, nullable=False) # e.g. "income <= 80000"
    error_message = Column(String, nullable=False)
