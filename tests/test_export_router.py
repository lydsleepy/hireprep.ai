import pytest
from unittest.mock import patch
from fastapi.testclient import TestClient


@pytest.fixture
def client():
    with patch("app.config.GEMINI_API_KEY", "test-key"), \
         patch("app.llm_client._client"):
        from app.main import app
        return TestClient(app)


def test_export_pdf_returns_pdf_bytes(client):
    with patch("app.doc_generator.to_pdf", return_value=b"%PDF-fake"):
        resp = client.post(
            "/api/export/pdf",
            json={"content": "Some output text", "filename": "cover_letter"},
        )
    assert resp.status_code == 200
    assert resp.headers["content-type"] == "application/pdf"
    assert "cover_letter.pdf" in resp.headers["content-disposition"]


def test_export_docx_returns_docx_bytes(client):
    with patch("app.doc_generator.to_docx", return_value=b"PK\x03\x04fake-docx"):
        resp = client.post(
            "/api/export/docx",
            json={"content": "Some output text", "filename": "tailored_resume"},
        )
    assert resp.status_code == 200
    assert "openxmlformats" in resp.headers["content-type"]
    assert "tailored_resume.docx" in resp.headers["content-disposition"]


def test_export_sanitizes_filename(client):
    with patch("app.doc_generator.to_pdf", return_value=b"%PDF-fake"):
        resp = client.post(
            "/api/export/pdf",
            json={"content": "text", "filename": "../../etc/passwd"},
        )
    assert resp.status_code == 200
    cd = resp.headers["content-disposition"]
    assert ".." not in cd
    assert ".pdf" in cd


def test_export_empty_filename_falls_back(client):
    with patch("app.doc_generator.to_pdf", return_value=b"%PDF-fake"):
        resp = client.post(
            "/api/export/pdf",
            json={"content": "text", "filename": ""},
        )
    assert resp.status_code == 200
    assert "hireprep_output" in resp.headers["content-disposition"]


def test_export_invalid_format_returns_422(client):
    resp = client.post(
        "/api/export/xlsx",
        json={"content": "text", "filename": "output"},
    )
    assert resp.status_code == 422
