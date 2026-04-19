import pytest
from app.doc_generator import to_pdf, to_docx


SAMPLE_TEXT = """\
EXPERIENCE

Software Engineer at Acme Corp
- Built a distributed caching layer that reduced API latency by 40%
- Led migration from monolith to microservices

EDUCATION

B.S. Computer Science, State University, 2020
"""


def test_to_pdf_returns_bytes():
    result = to_pdf(SAMPLE_TEXT, "test_output")
    assert isinstance(result, bytes)
    assert len(result) > 0


def test_to_pdf_starts_with_pdf_header():
    result = to_pdf(SAMPLE_TEXT, "test_output")
    assert result[:4] == b"%PDF"


def test_to_docx_returns_bytes():
    result = to_docx(SAMPLE_TEXT, "test_output")
    assert isinstance(result, bytes)
    assert len(result) > 0


def test_to_docx_is_valid_zip():
    """DOCX files are ZIP archives."""
    import zipfile
    import io
    result = to_docx(SAMPLE_TEXT, "test_output")
    assert zipfile.is_zipfile(io.BytesIO(result))


def test_to_pdf_handles_empty_text():
    result = to_pdf("", "empty")
    assert isinstance(result, bytes)


def test_to_docx_handles_empty_text():
    result = to_docx("", "empty")
    assert isinstance(result, bytes)
