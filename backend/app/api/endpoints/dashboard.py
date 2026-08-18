import datetime
from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func
from sqlalchemy.orm import Session
from backend.app.core.database import get_db
from backend.app.security.auth import get_current_user, RoleChecker
from backend.app.schemas import schemas
from backend.app.models.models import (
    Application, Escalation, Payment, Document, AuditLog, User
)

router = APIRouter()

@router.get("/metrics", response_model=schemas.DashboardMetrics)
def get_dashboard_metrics(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Computes system-wide KPIs for admin/officer dashboard (Section 24).
    """
    if current_user.role not in ["OFFICER", "ADMIN", "AUDITOR"]:
        raise HTTPException(status_code=403, detail="Access denied")

    # Counts
    total = db.query(Application).count()
    
    today_start = datetime.datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    today = db.query(Application).filter(Application.created_at >= today_start).count()
    
    completed = db.query(Application).filter(Application.status == "CERTIFICATE_READY").count()
    pending = db.query(Application).filter(Application.status.in_(["SUBMITTED", "UNDER_REVIEW", "DOCUMENT_VERIFICATION"])).count()
    failed = db.query(Application).filter(Application.status == "REJECTED").count()
    
    escalations = db.query(Escalation).filter(Escalation.status == "PENDING").count()
    
    # Calculate payment success rate
    payments = db.query(Payment).all()
    success_payments = sum(1 for p in payments if p.status == "SUCCESS")
    total_payments = len(payments)
    payment_rate = (success_payments / total_payments * 100) if total_payments > 0 else 100.0

    # Calculate document validation success rate
    docs = db.query(Document).all()
    success_docs = sum(1 for d in docs if d.status == "VALIDATED")
    total_docs = len(docs)
    doc_rate = (success_docs / total_docs * 100) if total_docs > 0 else 100.0

    # Mock latency averages
    avg_processing = 4.2 # hours
    avg_response = 210.0 # ms (simulated average LLM response latency)

    return schemas.DashboardMetrics(
        total_applications=total,
        applications_today=today,
        completed_applications=completed,
        pending_applications=pending,
        failed_applications=failed,
        escalations=escalations,
        avg_processing_time_hours=avg_processing,
        avg_response_latency_ms=avg_response,
        payment_success_rate=round(payment_rate, 2),
        doc_validation_success_rate=round(doc_rate, 2)
    )

@router.get("/charts", response_model=schemas.DashboardChartData)
def get_dashboard_chart_data(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Computes aggregated chart counts by category.
    """
    if current_user.role not in ["OFFICER", "ADMIN", "AUDITOR"]:
        raise HTTPException(status_code=403, detail="Access denied")

    # Group by Service
    services_query = db.query(Application.service_id, func.count(Application.id)).group_by(Application.service_id).all()
    services_map = {item[0]: item[1] for item in services_query}

    # Group by Language
    langs_query = db.query(Application.language, func.count(Application.id)).group_by(Application.language).all()
    langs_map = {item[0]: item[1] for item in langs_query}

    # Group by Channel
    channels_query = db.query(Application.channel, func.count(Application.id)).group_by(Application.channel).all()
    channels_map = {item[0]: item[1] for item in channels_query}

    # Group by Status
    status_query = db.query(Application.status, func.count(Application.id)).group_by(Application.status).all()
    status_map = {item[0]: item[1] for item in status_query}

    # Blocked requests (Data Sovereignty blocks)
    blocked_count = db.query(AuditLog).filter(AuditLog.action == "EXTERNAL_AI_REQUEST_BLOCKED").count()

    return schemas.DashboardChartData(
        services=services_map,
        languages=langs_map,
        channels=channels_map,
        statuses=status_map,
        blocked_requests=blocked_count
    )

@router.get("/audit", response_model=List[schemas.AuditLogOut])
def get_audit_logs(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Retrieves system audit logs (Section 23). Accessible to Officer, Admin, and Auditor.
    """
    if current_user.role not in ["OFFICER", "ADMIN", "AUDITOR"]:
        raise HTTPException(status_code=403, detail="Access denied")
        
    return db.query(AuditLog).order_by(AuditLog.timestamp.desc()).all()
