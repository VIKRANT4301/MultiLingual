import pytest
from backend.app.services.doc_intelligence import DocumentIntelligenceEngine

def test_fuzzy_name_matching():
    # Exact match
    assert DocumentIntelligenceEngine.compute_fuzzy_similarity("Vikram Patil", "Vikram Patil") == 1.0
    # Reordered tokens
    assert DocumentIntelligenceEngine.compute_fuzzy_similarity("Patil Vikram", "Vikram Patil") == 1.0
    # Slight variation
    sim = DocumentIntelligenceEngine.compute_fuzzy_similarity("Vikram R Patil", "Vikram Patil")
    assert sim >= 0.80
    # Discrepancy
    sim_diff = DocumentIntelligenceEngine.compute_fuzzy_similarity("Ramesh Kumar", "Vikram Patil")
    assert sim_diff < 0.50

def test_numeric_income_variance():
    # Exact income
    var, sim = DocumentIntelligenceEngine.compute_numeric_variance(450000, 450000)
    assert var == 0.0
    assert sim == 1.0

    # Slight variance (4.5L vs 4.6L)
    var, sim = DocumentIntelligenceEngine.compute_numeric_variance(450000, 460000)
    assert var <= 5.0
    assert sim == 1.0

    # Large variance (4.5L vs 9.5L)
    var, sim = DocumentIntelligenceEngine.compute_numeric_variance(450000, 950000)
    assert var > 50.0
    assert sim == 0.0

def test_cross_validate_document_matching():
    extracted = {
        "full_name": "Vikram Patil",
        "annual_income": 450000.0,
        "dob": "12-05-2002",
        "_ocr_confidence": 0.96
    }
    declared = {
        "full_name": "Vikram Patil",
        "annual_income": 450000.0,
        "dob": "12-05-2002"
    }

    result = DocumentIntelligenceEngine.cross_validate_document("income_proof", extracted, declared)
    assert result["status"] == "VALIDATED"
    assert result["confidence_score"] >= 0.90
    assert len(result["mismatches"]) == 0

def test_cross_validate_document_mismatch():
    extracted = {
        "full_name": "Ramesh Patil", # Mismatch
        "annual_income": 950000.0, # Large mismatch
        "dob": "12-05-2002",
        "_ocr_confidence": 0.90
    }
    declared = {
        "full_name": "Vikram Patil",
        "annual_income": 450000.0,
        "dob": "12-05-2002"
    }

    result = DocumentIntelligenceEngine.cross_validate_document("income_proof", extracted, declared)
    assert result["status"] in ["MISMATCH_DETECTED", "REVIEW_REQUIRED"]
    assert len(result["mismatches"]) >= 1
