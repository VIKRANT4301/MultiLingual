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
                "description": "Certificate proving residency in the state for 15+ years.",
                "required_documents": ["identity_proof", "address_proof", "residency_proof"],
                "fee": 50.0,
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
                "id": "nativity_certificate",
                "name": "Nativity Certificate",
                "description": "Certificate proving origin place nativity.",
                "required_documents": ["identity_proof", "birth_proof"],
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
                "id": "obc_ncl_certificate",
                "name": "OBC Non-Creamy Layer Certificate",
                "description": "OBC Non-Creamy Layer status for education and employment.",
                "required_documents": ["identity_proof", "caste_proof", "income_proof", "address_proof"],
                "fee": 50.0,
                "processing_days": 15
            },
            {
                "id": "ews_certificate",
                "name": "EWS Certificate",
                "description": "Economically Weaker Section eligibility certificate.",
                "required_documents": ["identity_proof", "income_proof", "property_documents"],
                "fee": 50.0,
                "processing_days": 15
            },
            {
                "id": "residence_certificate",
                "name": "Residence Certificate",
                "description": "Certificate verifying current residence address.",
                "required_documents": ["identity_proof", "address_proof"],
                "fee": 30.0,
                "processing_days": 7
            },
            {
                "id": "agricultural_land_certificate",
                "name": "Agricultural Land Certificate",
                "description": "Certificate proving land tenancy or ownership.",
                "required_documents": ["identity_proof", "land_records"],
                "fee": 75.0,
                "processing_days": 10
            },
            {
                "id": "minority_certificate",
                "name": "Minority Certificate",
                "description": "Certificate proving minority religion status.",
                "required_documents": ["identity_proof", "community_proof"],
                "fee": 50.0,
                "processing_days": 7
            },
            {
                "id": "widow_certificate",
                "name": "Widow Certificate",
                "description": "Certificate proving death of husband.",
                "required_documents": ["identity_proof", "marriage_certificate", "death_certificate"],
                "fee": 0.0,
                "processing_days": 7
            },
            {
                "id": "single_woman_certificate",
                "name": "Single Woman Certificate",
                "description": "Certificate proving single marital status.",
                "required_documents": ["identity_proof", "affidavit"],
                "fee": 0.0,
                "processing_days": 7
            },
            {
                "id": "handicap_disability_certificate",
                "name": "Disability Certificate",
                "description": "Certificate proving physical handicap status.",
                "required_documents": ["identity_proof", "medical_report"],
                "fee": 0.0,
                "processing_days": 15
            },
            {
                "id": "senior_citizen_certificate",
                "name": "Senior Citizen Certificate",
                "description": "Certificate verifying age 60 and above.",
                "required_documents": ["identity_proof", "age_proof"],
                "fee": 0.0,
                "processing_days": 5
            },
            {
                "id": "birth_certificate",
                "name": "Birth Certificate",
                "description": "Certificate registering birth details.",
                "required_documents": ["identity_proof", "hospital_records"],
                "fee": 25.0,
                "processing_days": 7
            },
            {
                "id": "death_certificate",
                "name": "Death Certificate",
                "description": "Certificate registering death details.",
                "required_documents": ["identity_proof", "hospital_records"],
                "fee": 25.0,
                "processing_days": 7
            },
            {
                "id": "marriage_certificate",
                "name": "Marriage Certificate",
                "description": "Certificate registering marriage details.",
                "required_documents": ["identity_proof", "witness_proof", "marriage_photos"],
                "fee": 100.0,
                "processing_days": 15
            },
            {
                "id": "legal_heir_certificate",
                "name": "Legal Heir Certificate",
                "description": "Certificate establishing succession family tree.",
                "required_documents": ["identity_proof", "death_certificate", "family_tree_affidavit"],
                "fee": 100.0,
                "processing_days": 30
            },
            {
                "id": "no_objection_certificate",
                "name": "No Objection Certificate",
                "description": "Purpose-specific NOC.",
                "required_documents": ["identity_proof", "application_form", "supporting_documents"],
                "fee": 50.0,
                "processing_days": 7
            },
            {
                "id": "character_certificate",
                "name": "Character Certificate",
                "description": "Police verified character certificate.",
                "required_documents": ["identity_proof", "passport_photo"],
                "fee": 50.0,
                "processing_days": 15
            },
            {
                "id": "non_encumbrance_certificate",
                "name": "Non-Encumbrance Certificate",
                "description": "Certificate verifying clear property title.",
                "required_documents": ["identity_proof", "property_documents"],
                "fee": 200.0,
                "processing_days": 15
            },
            {
                "id": "land_conversion_certificate",
                "name": "Land Conversion Certificate",
                "description": "Conversion from agricultural to non-agricultural land.",
                "required_documents": ["identity_proof", "survey_documents", "land_records"],
                "fee": 500.0,
                "processing_days": 30
            },
            {
                "id": "patta_transfer_certificate",
                "name": "Patta Transfer Certificate",
                "description": "Transfer of land ownership title records.",
                "required_documents": ["identity_proof", "patta_copy", "sale_deed"],
                "fee": 300.0,
                "processing_days": 15
            },
            {
                "id": "unemployed_certificate",
                "name": "Unemployed Certificate",
                "description": "Certificate verifying current unemployment status.",
                "required_documents": ["identity_proof", "affidavit"],
                "fee": 30.0,
                "processing_days": 7
            },
            {
                "id": "student_certificate",
                "name": "Student Certificate",
                "description": "Certificate proving enrollment in school/college.",
                "required_documents": ["identity_proof", "school_college_letter"],
                "fee": 20.0,
                "processing_days": 3
            }
        ]

        for s_data in services:
            existing = db.query(models.Service).filter(models.Service.id == s_data["id"]).first()
            if not existing:
                srv = models.Service(**s_data)
                db.add(srv)
            else:
                # Update existing records to ensure we have all 25 corrected in DB
                for key, val in s_data.items():
                    setattr(existing, key, val)
        db.commit()

        # Seed Service Rules
        rules = [
            {
                "service_id": "income_certificate",
                "rule_name": "Max Income Threshold Check",
                "rule_condition": "annual_income <= 1500000",
                "error_message": "Income exceeds maximum threshold (Rs. 15 Lakhs)"
            },
            {
                "service_id": "obc_ncl_certificate",
                "rule_name": "Creamy Layer Check",
                "rule_condition": "annual_income <= 800000",
                "error_message": "Income exceeds Non-Creamy Layer threshold (Rs. 8 Lakhs)"
            },
            {
                "service_id": "ews_certificate",
                "rule_name": "EWS Income Check",
                "rule_condition": "annual_income <= 800000",
                "error_message": "Income exceeds EWS category threshold (Rs. 8 Lakhs)"
            }
        ]

        for r_data in rules:
            existing = db.query(models.ServiceRule).filter(
                models.ServiceRule.service_id == r_data["service_id"],
                models.ServiceRule.rule_name == r_data["rule_name"]
            ).first()
            if not existing:
                rule = models.ServiceRule(**r_data)
                db.add(rule)
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

# Mount static frontend build files at the very end of startup
frontend_dist_dir = os.path.join(os.path.dirname(__file__), "..", "frontend", "dist")
if not os.path.exists(frontend_dist_dir):
    os.makedirs(frontend_dist_dir, exist_ok=True)
    placeholder_file = os.path.join(frontend_dist_dir, "index.html")
    if not os.path.exists(placeholder_file):
        with open(placeholder_file, "w") as f:
            f.write("<h1>Loading React Native Frontend...</h1>")

app.mount("/", StaticFiles(directory=frontend_dist_dir, html=True), name="frontend")

