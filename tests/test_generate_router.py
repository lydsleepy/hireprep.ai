import pytest
from unittest.mock import patch
from fastapi.testclient import TestClient


@pytest.fixture
def client():
    with patch("app.config.GEMINI_API_KEY", "test-key"), \
         patch("app.llm_client._client"):
        from app.main import app
        return TestClient(app)


def test_generate_cover_letter_missing_jd(client):
    resp = client.post(
        "/api/generate/cover_letter",
        data={"jd_text": "short"},  # < 50 chars
    )
    assert resp.status_code == 400
    assert "50 characters" in resp.json()["detail"]


def test_generate_cover_letter_missing_resume(client):
    resp = client.post(
        "/api/generate/cover_letter",
        data={"jd_text": "We are looking for a software engineer with 5+ years experience in Python and distributed systems."},
    )
    assert resp.status_code == 400
    assert "resume" in resp.json()["detail"].lower()


def test_generate_practice_questions_no_resume_ok(client):
    """Practice questions feature should work without a resume."""
    # Patch in the router's namespace — router uses `from app.llm_client import generate`
    with patch("app.routers.generate.generate", return_value="Behavioral\n1. Tell me about yourself."):
        resp = client.post(
            "/api/generate/practice_questions",
            data={"jd_text": "We are looking for a software engineer with 5+ years experience in Python and distributed systems."},
        )
    assert resp.status_code == 200
    assert "output" in resp.json()


def test_generate_invalid_feature(client):
    resp = client.post(
        "/api/generate/nonexistent_feature",
        data={"jd_text": "We are looking for a software engineer with 5+ years experience in Python and distributed systems."},
    )
    assert resp.status_code == 422  # FastAPI enum validation


def test_generate_cover_letter_with_resume_and_jd(client):
    # Patch in the router's namespace — router uses `from ... import` for both
    with patch("app.routers.generate.extract_resume_text", return_value="John Doe\nSoftware Engineer\n5 years experience in Python and distributed systems development at large scale"), \
         patch("app.routers.generate.generate", return_value="Dear Hiring Team,\n\nI am a great fit for this role."):
        resp = client.post(
            "/api/generate/cover_letter",
            data={"jd_text": "We are looking for a software engineer with 5+ years experience in Python and distributed systems."},
            files={"resume_file": ("resume.pdf", b"fake-pdf-bytes", "application/pdf")},
        )
    assert resp.status_code == 200
    assert resp.json()["output"] == "Dear Hiring Team,\n\nI am a great fit for this role."


def test_generate_returns_502_on_llm_error(client):
    from app.llm_client import LLMError
    with patch("app.routers.generate.extract_resume_text", return_value="John Doe\nSoftware Engineer with extensive background in Python development and distributed systems architecture"), \
         patch("app.routers.generate.generate", side_effect=LLMError("API unavailable")):
        resp = client.post(
            "/api/generate/cover_letter",
            data={"jd_text": "We are looking for a software engineer with 5+ years experience in Python and distributed systems."},
            files={"resume_file": ("resume.pdf", b"fake-pdf-bytes", "application/pdf")},
        )
    assert resp.status_code == 502
