import os
import logging
from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session

from backend.app.core.config import settings
from backend.app.core.database import engine, Base, get_db
from backend.app.models import models
from backend.app.security import auth

# Import routers
from backend.app.api.endpoints import (
    auth as auth_router,
    conversation as conversation_router,
    applications as applications_router,
    adapters as adapters_router,
    dashboard as dashboard_router
)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create tables in Database (automatic initialization/migration style)
try:
    Base.metadata.create_all(bind=engine)
    logger.info("Database tables initialized successfully.")
except Exception as e:
    logger.error(f"Error creating database tables: {e}")

app = FastAPI(
    title=settings.PROJECT_NAME,
    version="1.0.0",
    openapi_url=f"{settings.API_V1_STR}/openapi.json"
)

# Set up CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # For POC, allow all. In prod, restrict.
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files directories (for downloading generated files/receipts/certificates)
static_certificates_dir = os.path.join(os.path.dirname(__file__), "..", "data", "synthetic")
os.makedirs(static_certificates_dir, exist_ok=True)
app.mount("/static/certificates", StaticFiles(directory=static_certificates_dir), name="certificates")

# Include API Routers
app.include_router(auth_router.router, prefix=f"{settings.API_V1_STR}/auth", tags=["Authentication"])
app.include_router(conversation_router.router, prefix=f"{settings.API_V1_STR}/conversation", tags=["Conversations"])
app.include_router(applications_router.router, prefix=f"{settings.API_V1_STR}/applications", tags=["Applications"])
app.include_router(adapters_router.router, prefix=f"{settings.API_V1_STR}/adapters", tags=["Adapters"])
app.include_router(dashboard_router.router, prefix=f"{settings.API_V1_STR}/dashboard", tags=["Dashboard"])

@app.get("/health")
def health_check():
    """
    Health check endpoint (Section 25)
    """
    return {"status": "healthy", "timestamp": "ok"}

@app.get("/ready")
def readiness_check(db: Session = Depends(get_db)):
    """
    Readiness check verifying database connectivity.
    """
    try:
        # Execute simple query
        db.query(models.Service).first()
        return {"status": "ready"}
    except Exception as e:
        logger.error(f"Readiness check failed: {e}")
        return {"status": "not ready", "error": str(e)}

@app.on_event("startup")
def seed_database():
    """
    Seeds initial services, users, and synthetic citizen personas (Section 21, 35).
    """
    db = next(get_db())
    try:
        # 1. Seed Services
        services = [
            {
                "id": "income_certificate",
                "name": "Income Certificate",
                "description": "Certificate proving annual family income.",
                "required_documents": ["identity_proof", "address_proof", "income_proof"],
                "fee": 50.0,
                "processing_days": 7
            },
            {
                "id": "domicile_certificate",
                "name": "Domicile Certificate",
                "description": "Certificate proving residency in the state.",
                "required_documents": ["identity_proof", "address_proof", "residency_proof"],
                "fee": 60.0,
                "processing_days": 15
            },
            {
                "id": "caste_certificate",
                "name": "Caste Certificate",
                "description": "Certificate proving caste community classification.",
                "required_documents": ["identity_proof", "caste_proof"],
                "fee": 50.0,
                "processing_days": 10
            },
            {
                "id": "solvency_certificate",
                "name": "Solvency Certificate",
                "description": "Certificate proving financial creditworthiness.",
                "required_documents": ["identity_proof", "bank_statement", "asset_proof"],
                "fee": 100.0,
                "processing_days": 21
            },
            {
                "id": "nativity_certificate",
                "name": "Nativity Certificate",
                "description": "Certificate proving origin place nativity.",
                "required_documents": ["identity_proof", "birth_proof"],
                "fee": 50.0,
                "processing_days": 10
            }
        ]

        for s_data in services:
            existing = db.query(models.Service).filter(models.Service.id == s_data["id"]).first()
            if not existing:
                srv = models.Service(**s_data)
                db.add(srv)
        db.commit()

        # 2. Seed Users & Personas (Section 22 & 35)
        # Seed Administrator
        admin = db.query(models.User).filter(models.User.username == "admin").first()
        if not admin:
            db.add(models.User(
                username="admin",
                hashed_password=auth.get_password_hash("admin123"),
                role="ADMIN"
            ))
            
        # Seed Officer
        officer = db.query(models.User).filter(models.User.username == "officer").first()
        if not officer:
            db.add(models.User(
                username="officer",
                hashed_password=auth.get_password_hash("officer123"),
                role="OFFICER"
            ))

        # Seed Auditor
        auditor = db.query(models.User).filter(models.User.username == "auditor").first()
        if not auditor:
            db.add(models.User(
                username="auditor",
                hashed_password=auth.get_password_hash("auditor123"),
                role="AUDITOR"
            ))

        # Seed Citizen
        citizen_user = db.query(models.User).filter(models.User.username == "citizen").first()
        if not citizen_user:
            c_user = models.User(
                username="citizen",
                hashed_password=auth.get_password_hash("citizen123"),
                role="CITIZEN"
            )
            db.add(c_user)
            db.commit()
            db.refresh(c_user)
            
            # Link citizen details
            c_profile = models.Citizen(
                user_id=c_user.id,
                full_name="Synthetic Citizen A",
                phone_number="9876543210",
                email="citizen.a@synthetic.gov.in",
                address="102, Shanti Nagar, Nagpur",
                preferred_language="mr"
            )
            db.add(c_profile)
        
        db.commit()
        logger.info("Initial services, users, and synthetic personas seeded.")
    except Exception as e:
        logger.error(f"Error seeding database: {e}")
        db.rollback()
    finally:
        db.close()
