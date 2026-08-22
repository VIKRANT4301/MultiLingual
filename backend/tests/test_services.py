import os
import yaml
import glob
from sqlalchemy.orm import Session
from backend.app.models.models import Service
from backend.app.core.database import SessionLocal

def test_yaml_files_exist():
    # Verify that the expected configuration files exist in the services directory
    services_dir = os.path.join(os.path.dirname(__file__), "..", "..", "services")
    assert os.path.exists(services_dir), f"Services directory not found at {services_dir}"
    
    yaml_files = glob.glob(os.path.join(services_dir, "*.yaml"))
    assert len(yaml_files) >= 5, "Expected at least 5 YAML configurations in services/"
    
    # Check that each YAML has the required keys
    for filepath in yaml_files:
        with open(filepath, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
            assert "id" in data, f"Missing 'id' in {filepath}"
            assert "name" in data, f"Missing 'name' in {filepath}"
            assert "required_documents" in data, f"Missing 'required_documents' in {filepath}"
            assert "fee" in data, f"Missing 'fee' in {filepath}"

def test_services_loaded_in_db():
    # Verify that services seeded from YAML are present in the SQLite database
    db: Session = SessionLocal()
    try:
        services = db.query(Service).all()
        assert len(services) >= 25, f"Expected at least 25 seeded services in DB, got {len(services)}"
        
        # Verify that specific config overrides are stored
        income_cert = db.query(Service).filter(Service.id == "income_certificate").first()
        assert income_cert is not None
        assert income_cert.fee == 50.0
        assert "income_proof" in income_cert.required_documents
        
        domicile_cert = db.query(Service).filter(Service.id == "domicile_certificate").first()
        assert domicile_cert is not None
        assert domicile_cert.fee == 50.0
        assert "residency_proof" in domicile_cert.required_documents
    finally:
        db.close()
