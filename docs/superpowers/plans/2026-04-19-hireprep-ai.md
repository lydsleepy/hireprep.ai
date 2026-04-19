# hireprep.ai Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a full-stack web app that accepts a resume + job description and generates cover letters, practice questions, and a tailored resume via Gemini AI.

**Architecture:** FastAPI backend serves both static files and a JSON API; the frontend is plain HTML/CSS/vanilla JS with no build step. Resume parsing, LLM calls, and document generation are each isolated in their own module. All user data is ephemeral — nothing is persisted server-side or in browser storage.

**Tech Stack:** Python 3.14.3, FastAPI, Uvicorn, google-genai (Gemini 2.5 Flash), pypdf, python-docx, reportlab, plain HTML + CSS + ES2022 JS.

---

## File Map

| File | Responsibility |
|------|---------------|
| `requirements.txt` | Pinned deps |
| `.env.example` | Key placeholder |
| `.gitignore` | Excludes `.env`, caches, venvs |
| `run.sh` | One-command bootstrap + server start |
| `app/__init__.py` | Package marker |
| `app/config.py` | Env loading, constants, fail-fast key check |
| `app/llm_client.py` | Gemini wrapper, `LLMError`, `generate()` |
| `app/resume_parser.py` | `extract_resume_text()` for pdf/docx, `.doc` guard |
| `app/prompts.py` | Four system prompt constants, `build_user_content()` |
| `app/doc_generator.py` | `to_pdf()` and `to_docx()` → bytes |
| `app/routers/__init__.py` | Package marker |
| `app/routers/generate.py` | `POST /api/generate/{feature}` |
| `app/routers/export.py` | `POST /api/export/{format}` |
| `app/main.py` | FastAPI app wiring, CORS, static mount, size limit |
| `static/index.html` | Full single-page markup |
| `static/css/styles.css` | All styles — neumorphic, Inter, responsive |
| `static/js/app.js` | All interactivity — state, fetch, modal, download |
| `static/favicon.svg` | Two-square favicon mark |
| `static/assets/logo.svg` | Full wordmark with mark |
| `tests/test_resume_parser.py` | Unit tests for parser |
| `tests/test_doc_generator.py` | Unit tests for doc generator |
| `tests/test_generate_router.py` | Integration tests for generate endpoint |
| `tests/test_export_router.py` | Integration tests for export endpoint |
| `README.md` | Setup and run instructions |
| `PROJECT_DOCS.md` | Full architecture + design documentation |

---

## Task 1: Project scaffolding

**Files:**
- Create: `requirements.txt`
- Create: `.env.example`
- Create: `.gitignore`
- Create: `run.sh`
- Create: `app/__init__.py`
- Create: `app/routers/__init__.py`
- Create: `tests/__init__.py`
- Create: `static/css/` and `static/js/` directories

- [ ] **Step 1: Create `requirements.txt`**

```
fastapi>=0.115.0
uvicorn[standard]>=0.32.0
python-dotenv>=1.0.0
python-multipart>=0.0.12
google-genai>=1.0.0
pypdf>=5.0.0
python-docx>=1.1.0
reportlab>=4.2.0
pydantic>=2.0.0
httpx>=0.27.0
pytest>=8.0.0
pytest-asyncio>=0.24.0
```

- [ ] **Step 2: Create `.env.example`**

```
GEMINI_API_KEY=your_key_here
```

- [ ] **Step 3: Create `.gitignore`**

```
.env
__pycache__/
*.pyc
.venv/
venv/
.DS_Store
*.tmp
dist/
*.egg-info/
.pytest_cache/
```

- [ ] **Step 4: Create `run.sh`**

```bash
#!/usr/bin/env bash
set -e
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

- [ ] **Step 5: Make run.sh executable and create package markers**

```bash
chmod +x run.sh
touch app/__init__.py app/routers/__init__.py tests/__init__.py
mkdir -p static/css static/js static/assets
```

- [ ] **Step 6: Commit**

```bash
git add requirements.txt .env.example .gitignore run.sh app/__init__.py app/routers/__init__.py tests/__init__.py static/css/.gitkeep static/js/.gitkeep static/assets/.gitkeep
git commit -m "chore: project scaffolding and configuration files"
```

---

## Task 2: Config module

**Files:**
- Create: `app/config.py`

- [ ] **Step 1: Write `app/config.py`**

```python
import os
from dotenv import load_dotenv

load_dotenv()

GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")
GEMINI_MODEL: str = "gemini-2.5-flash"
MAX_UPLOAD_MB: int = 5
MAX_UPLOAD_BYTES: int = MAX_UPLOAD_MB * 1024 * 1024

ALLOWED_EXTENSIONS: set[str] = {".pdf", ".docx", ".doc"}
ALLOWED_MIME_TYPES: set[str] = {
    "application/pdf",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "application/msword",
}

def validate_config() -> None:
    """Fail fast at startup if required config is missing."""
    if not GEMINI_API_KEY:
        raise RuntimeError(
            "GEMINI_API_KEY is not set. "
            "Copy .env.example to .env and add your Gemini API key."
        )
```

- [ ] **Step 2: Commit**

```bash
git add app/config.py
git commit -m "feat: add config module with env loading and fail-fast validation"
```

---

## Task 3: Resume parser

**Files:**
- Create: `app/resume_parser.py`
- Create: `tests/test_resume_parser.py`

- [ ] **Step 1: Write failing tests**

```python
# tests/test_resume_parser.py
import pytest
from app.resume_parser import extract_resume_text


def test_raises_on_doc_format():
    with pytest.raises(ValueError, match="Legacy .doc format"):
        extract_resume_text(b"fake content", "resume.doc")


def test_raises_on_unsupported_extension():
    with pytest.raises(ValueError, match="Unsupported file type"):
        extract_resume_text(b"fake content", "resume.txt")


def test_raises_on_empty_pdf():
    # A valid but text-empty PDF (minimal PDF structure)
    minimal_pdf = b"%PDF-1.4\n1 0 obj\n<< /Type /Catalog >>\nendobj\nxref\n0 1\n0000000000 65535 f \ntrailer\n<< /Size 1 /Root 1 0 R >>\nstartxref\n9\n%%EOF"
    with pytest.raises(ValueError, match="couldn't read any text"):
        extract_resume_text(minimal_pdf, "empty.pdf")


def test_raises_on_short_text_pdf(tmp_path):
    # We'll test with a real pypdf-generated short-text scenario via mocking
    from unittest.mock import patch, MagicMock
    mock_reader = MagicMock()
    mock_page = MagicMock()
    mock_page.extract_text.return_value = "Hi"
    mock_reader.pages = [mock_page]
    with patch("app.resume_parser.PdfReader", return_value=mock_reader):
        with pytest.raises(ValueError, match="couldn't read any text"):
            extract_resume_text(b"fakepdf", "short.pdf")


def test_pdf_extraction_returns_stripped_text():
    from unittest.mock import patch, MagicMock
    mock_reader = MagicMock()
    mock_page = MagicMock()
    mock_page.extract_text.return_value = "  John Doe\n\n\nSoftware Engineer at Acme Corp\n\n"
    mock_reader.pages = [mock_page]
    with patch("app.resume_parser.PdfReader", return_value=mock_reader):
        result = extract_resume_text(b"fakepdf", "resume.pdf")
    assert "John Doe" in result
    assert "Software Engineer" in result
    # Should not have more than one consecutive blank line
    assert "\n\n\n" not in result


def test_docx_extraction_includes_table_text():
    from unittest.mock import patch, MagicMock
    mock_doc = MagicMock()
    mock_para = MagicMock()
    mock_para.text = "John Doe - Software Engineer"
    mock_cell = MagicMock()
    mock_cell.text = "Python | JavaScript | SQL"
    mock_row = MagicMock()
    mock_row.cells = [mock_cell]
    mock_table = MagicMock()
    mock_table.rows = [mock_row]
    mock_doc.paragraphs = [mock_para]
    mock_doc.tables = [mock_table]
    with patch("app.resume_parser.Document", return_value=mock_doc):
        result = extract_resume_text(b"fakedocx", "resume.docx")
    assert "John Doe" in result
    assert "Python" in result
```

- [ ] **Step 2: Run tests to confirm they fail**

```bash
cd /Users/lydia/code/personal/hireprep.ai
source .venv/bin/activate && pytest tests/test_resume_parser.py -v 2>&1 | head -30
```

Expected: ImportError or ModuleNotFoundError for `app.resume_parser`

- [ ] **Step 3: Write `app/resume_parser.py`**

```python
import io
import re
from pathlib import Path

from pypdf import PdfReader
from docx import Document


_MIN_TEXT_LENGTH = 100


def extract_resume_text(file_bytes: bytes, filename: str) -> str:
    """Extract plain text from a PDF or DOCX resume.

    Raises ValueError with user-facing messages on unsupported formats,
    unreadable files, or files with too little extracted text.
    """
    suffix = Path(filename).suffix.lower()

    if suffix == ".doc":
        raise ValueError(
            "Legacy .doc format isn't supported. Please save your resume as "
            ".docx or .pdf and try again."
        )
    if suffix == ".pdf":
        return _extract_pdf(file_bytes)
    if suffix == ".docx":
        return _extract_docx(file_bytes)

    raise ValueError(
        f"Unsupported file type '{suffix}'. Please upload a .pdf or .docx file."
    )


def _extract_pdf(file_bytes: bytes) -> str:
    reader = PdfReader(io.BytesIO(file_bytes))
    pages = [page.extract_text() or "" for page in reader.pages]
    raw = "\n".join(pages)
    text = _clean(raw)
    _require_min_text(text)
    return text


def _extract_docx(file_bytes: bytes) -> str:
    doc = Document(io.BytesIO(file_bytes))

    parts: list[str] = []

    for para in doc.paragraphs:
        if para.text.strip():
            parts.append(para.text.strip())

    # Resumes often use tables for layout — extract those too
    for table in doc.tables:
        for row in table.rows:
            row_texts = [cell.text.strip() for cell in row.cells if cell.text.strip()]
            if row_texts:
                parts.append("  ".join(row_texts))

    text = _clean("\n".join(parts))
    _require_min_text(text)
    return text


def _clean(text: str) -> str:
    """Collapse excessive blank lines and strip leading/trailing whitespace."""
    text = text.strip()
    # Replace 3+ consecutive newlines with 2
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text


def _require_min_text(text: str) -> None:
    if len(text) < _MIN_TEXT_LENGTH:
        raise ValueError(
            "We couldn't read any text from this file. If it's a scanned image, "
            "please upload a text-based PDF or .docx instead."
        )
```

- [ ] **Step 4: Run tests and confirm they pass**

```bash
pytest tests/test_resume_parser.py -v
```

Expected: All 6 tests PASS

- [ ] **Step 5: Commit**

```bash
git add app/resume_parser.py tests/test_resume_parser.py
git commit -m "feat: add resume parser with PDF and DOCX extraction"
```

---

## Task 4: LLM client

**Files:**
- Create: `app/llm_client.py`

Note: We don't write a test that actually calls Gemini (costs money, requires network). We test the error-wrapping logic with mocks.

- [ ] **Step 1: Write `app/llm_client.py`**

```python
from google import genai
from google.genai import types as genai_types

from app.config import GEMINI_API_KEY, GEMINI_MODEL


class LLMError(Exception):
    """Raised when the Gemini API call fails."""


def generate(
    system_prompt: str,
    user_content: str,
    temperature: float = 0.7,
) -> str:
    """Call Gemini and return the response text.

    Raises LLMError on any API failure so callers can convert to HTTP 502.
    """
    client = genai.Client(api_key=GEMINI_API_KEY)

    config = genai_types.GenerateContentConfig(
        system_instruction=system_prompt,
        temperature=temperature,
    )

    try:
        response = client.models.generate_content(
            model=GEMINI_MODEL,
            contents=user_content,
            config=config,
        )
    except Exception as exc:
        raise LLMError(f"Gemini API call failed: {exc}") from exc

    text = response.text
    if not text or not text.strip():
        raise LLMError("Gemini returned an empty response.")

    return text.strip()
```

- [ ] **Step 2: Commit**

```bash
git add app/llm_client.py
git commit -m "feat: add Gemini LLM client with error wrapping"
```

---

## Task 5: Prompts module

**Files:**
- Create: `app/prompts.py`

- [ ] **Step 1: Write `app/prompts.py`**

```python
COVER_LETTER_PROMPT = """\
You are a professional cover letter writer helping a job seeker. Given the candidate's resume and a target job description, write a personalized cover letter.

Requirements:
- Length: 280–380 words
- Structure: a specific opening hook, two body paragraphs, a confident closing paragraph, and a signoff using the candidate's actual name from the resume
- Tie specific experiences from the resume to specific requirements in the job description
- Use natural, specific, confident language

Hard rules (these override all other instructions):
1. Never fabricate experience, employers, titles, dates, metrics, or skills that are not in the resume
2. Never claim a personal or emotional history with the company that isn't supported by the inputs (no "I've always admired..." unless the resume literally shows it)
3. Avoid AI-sounding phrases and clichés: "I am thrilled to apply", "As a highly motivated individual", "In today's fast-paced world", "leveraging", "synergy", "passionate about", "dynamic professional", "proven track record", "results-driven", "I am writing to express my interest"
4. Do not use em dashes as a stylistic flourish. Use periods, commas, or colons instead
5. Do not invent a hiring manager name. If the JD doesn't specify one, use "Dear Hiring Team,"
6. Output only the cover letter text — no preamble, no markdown, no explanation, no notes at the end\
"""

PRACTICE_QUESTIONS_PROMPT = """\
You are an experienced interviewer preparing a candidate for an interview. Given a job description (and optionally the candidate's resume), generate 12 realistic interview questions a hiring manager would plausibly ask for this role.

Question mix:
- 3–4 behavioral questions
- 3–4 technical or role-specific questions
- 2–3 background/experience questions
- 2–3 situational or problem-solving questions

If a resume is provided, tailor 3–4 of the questions to specific experiences or skills the candidate lists — but keep them realistic, not overly specific gotchas.

Output format (plain text, exactly this structure):

Behavioral
1. [question]
2. [question]
...

Technical
1. [question]
...

Background
1. [question]
...

Situational
1. [question]
...

Hard rules:
- Do not invent details about the company beyond what the JD states
- Do not write leading or loaded questions
- Do not include answers, hints, or coaching — questions only
- Each question should be answerable in 2–5 minutes of speaking
- Output only the formatted question list — no preamble, no closing notes, no markdown headers with `#`\
"""

RESUME_QUESTIONS_PROMPT = """\
You are a skilled interviewer who probes candidate resumes for depth. Given the candidate's resume and the target job description, generate 12 questions an interviewer would most likely ask THIS specific candidate.

Focus on:
- Specific projects, roles, or achievements listed on the resume
- Transitions, apparent gaps, or career pivots
- Skills listed but not clearly demonstrated in project descriptions
- How this candidate's experience maps to the target role
- Reasonable probes about how they achieved things they claim

Output format (plain text, exactly this structure):

1. [Category in brackets, e.g. "Project Deep-Dive"] — [question]
2. [Category] — [question]
...

Hard rules:
- Only reference content actually present in the resume. Do not invent projects, employers, or accomplishments
- Avoid judgmental or "gotcha" framing. The tone is curious, not adversarial
- Do not include answers, hints, or coaching
- Cover at least 4 different items from the resume
- Output only the numbered list — no preamble, no markdown headers, no closing notes\
"""

TAILORED_RESUME_PROMPT = """\
You are a resume editor. Given a candidate's current resume and a target job description, produce a tailored version of the resume optimized for this specific role.

Hard rules — these take absolute precedence:
1. Never add experience, credentials, skills, employers, dates, job titles, degrees, or achievements that are not present in the original resume
2. Never inflate numbers, metrics, percentages, team sizes, or outcomes beyond what the original states
3. Never change employer names, job titles, employment dates, or degree/institution information
4. Never invent technical skills the candidate didn't list

You may:
- Reorder sections and bullets to foreground the most relevant experience
- Rewrite existing bullet points with stronger action verbs and clearer structure
- Rewrite the professional summary (if one exists) to emphasize relevant strengths
- Incorporate keywords from the JD ONLY where they truthfully describe the candidate's existing experience
- Trim less-relevant bullets (but do not delete entire roles, degrees, or positions)

Preserve the original structure: contact block, summary (if present), experience, education, skills, projects, and any other sections the candidate included.

Output format: plain text resume. Section headers in ALL CAPS on their own line. Dashes (`-`) for bullet points. Blank line between sections. No markdown syntax (no `**`, no `#`, no `>`). The output should paste cleanly into a resume document.

Output only the tailored resume text — no preamble, no explanation, no notes about what you changed.\
"""

# Maps feature key to (prompt constant, temperature)
FEATURE_CONFIG: dict[str, tuple[str, float]] = {
    "cover_letter": (COVER_LETTER_PROMPT, 0.7),
    "practice_questions": (PRACTICE_QUESTIONS_PROMPT, 0.7),
    "resume_questions": (RESUME_QUESTIONS_PROMPT, 0.7),
    "tailored_resume": (TAILORED_RESUME_PROMPT, 0.4),
}


def build_user_content(resume_text: str | None, jd_text: str) -> str:
    """Format the user-side input block with clearly labeled sections."""
    parts = []
    if resume_text:
        parts.append(f"[RESUME]\n{resume_text}")
    parts.append(f"[JOB DESCRIPTION]\n{jd_text}")
    return "\n\n".join(parts)
```

- [ ] **Step 2: Commit**

```bash
git add app/prompts.py
git commit -m "feat: add system prompts and user content builder"
```

---

## Task 6: Document generator

**Files:**
- Create: `app/doc_generator.py`
- Create: `tests/test_doc_generator.py`

- [ ] **Step 1: Write failing tests**

```python
# tests/test_doc_generator.py
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
```

- [ ] **Step 2: Run tests to confirm they fail**

```bash
pytest tests/test_doc_generator.py -v 2>&1 | head -20
```

Expected: ImportError for `app.doc_generator`

- [ ] **Step 3: Write `app/doc_generator.py`**

```python
import io
import re

from reportlab.lib.pagesizes import LETTER
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.enums import TA_LEFT

from docx import Document as DocxDocument
from docx.shared import Inches, Pt
from docx.oxml.ns import qn


def to_pdf(text: str, title: str) -> bytes:
    """Render plain text to a PDF and return the bytes."""
    buf = io.BytesIO()

    doc = SimpleDocTemplate(
        buf,
        pagesize=LETTER,
        leftMargin=inch,
        rightMargin=inch,
        topMargin=inch,
        bottomMargin=inch,
        title=title,
    )

    styles = getSampleStyleSheet()
    body_style = ParagraphStyle(
        "body",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=11,
        leading=17,
        spaceAfter=6,
        alignment=TA_LEFT,
    )

    story = []
    paragraphs = text.split("\n\n") if text else [""]

    for para in paragraphs:
        para = para.strip()
        if not para:
            story.append(Spacer(1, 6))
            continue

        # Escape XML special chars that reportlab chokes on
        para = para.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

        # Preserve line breaks within a paragraph using <br/>
        para = para.replace("\n", "<br/>")
        story.append(Paragraph(para, body_style))

    doc.build(story)
    return buf.getvalue()


def to_docx(text: str, title: str) -> bytes:
    """Render plain text to a DOCX and return the bytes."""
    document = DocxDocument()

    # Set 1-inch margins on all sections
    for section in document.sections:
        section.top_margin = Inches(1)
        section.bottom_margin = Inches(1)
        section.left_margin = Inches(1)
        section.right_margin = Inches(1)

    lines = text.split("\n") if text else [""]

    for line in lines:
        stripped = line.strip()
        para = document.add_paragraph()
        run = para.add_run(stripped)

        # Bold lines that look like section headers:
        # ALL CAPS lines or lines that are just a label ending with ":"
        if stripped and (stripped == stripped.upper() or stripped.endswith(":")):
            run.bold = True

        run.font.name = "Calibri"
        run.font.size = Pt(11)

        # Minimal spacing
        para.paragraph_format.space_before = Pt(0)
        para.paragraph_format.space_after = Pt(2)

    buf = io.BytesIO()
    document.save(buf)
    return buf.getvalue()
```

- [ ] **Step 4: Run tests and confirm they pass**

```bash
pytest tests/test_doc_generator.py -v
```

Expected: All 6 tests PASS

- [ ] **Step 5: Commit**

```bash
git add app/doc_generator.py tests/test_doc_generator.py
git commit -m "feat: add PDF and DOCX document generators"
```

---

## Task 7: Generate router

**Files:**
- Create: `app/routers/generate.py`
- Create: `tests/test_generate_router.py`

- [ ] **Step 1: Write failing tests**

```python
# tests/test_generate_router.py
import pytest
from unittest.mock import patch, AsyncMock, MagicMock
from fastapi.testclient import TestClient


@pytest.fixture
def client():
    # Import after patching config to avoid GEMINI_API_KEY check
    with patch("app.config.GEMINI_API_KEY", "test-key"):
        from app.main import app
        return TestClient(app)


def _make_pdf_bytes():
    """Minimal PDF that pypdf can parse (single page, short text for mock)."""
    return b"fake-pdf-content"


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
    with patch("app.llm_client.generate", return_value="Behavioral\n1. Tell me about yourself."):
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
    with patch("app.resume_parser.extract_resume_text", return_value="John Doe\nSoftware Engineer\n5 years experience"), \
         patch("app.llm_client.generate", return_value="Dear Hiring Team,\n\nI am a great fit for this role."):
        resp = client.post(
            "/api/generate/cover_letter",
            data={"jd_text": "We are looking for a software engineer with 5+ years experience in Python and distributed systems."},
            files={"resume_file": ("resume.pdf", b"fake-pdf-bytes", "application/pdf")},
        )
    assert resp.status_code == 200
    assert resp.json()["output"] == "Dear Hiring Team,\n\nI am a great fit for this role."


def test_generate_returns_502_on_llm_error(client):
    from app.llm_client import LLMError
    with patch("app.resume_parser.extract_resume_text", return_value="John Doe\nSoftware Engineer with extensive background in Python development and distributed systems architecture"), \
         patch("app.llm_client.generate", side_effect=LLMError("API unavailable")):
        resp = client.post(
            "/api/generate/cover_letter",
            data={"jd_text": "We are looking for a software engineer with 5+ years experience in Python and distributed systems."},
            files={"resume_file": ("resume.pdf", b"fake-pdf-bytes", "application/pdf")},
        )
    assert resp.status_code == 502
```

- [ ] **Step 2: Run tests to confirm they fail**

```bash
pytest tests/test_generate_router.py -v 2>&1 | head -30
```

Expected: ImportError or test failures

- [ ] **Step 3: Write `app/routers/generate.py`**

```python
from enum import Enum
from typing import Annotated

from fastapi import APIRouter, Form, HTTPException, UploadFile, File
from fastapi.responses import JSONResponse

from app.config import MAX_UPLOAD_BYTES
from app.llm_client import generate, LLMError
from app.prompts import FEATURE_CONFIG, build_user_content
from app.resume_parser import extract_resume_text


router = APIRouter()


class Feature(str, Enum):
    cover_letter = "cover_letter"
    practice_questions = "practice_questions"
    resume_questions = "resume_questions"
    tailored_resume = "tailored_resume"


# Features that require a resume
_RESUME_REQUIRED = {Feature.cover_letter, Feature.resume_questions, Feature.tailored_resume}


@router.post("/api/generate/{feature}")
async def generate_feature(
    feature: Feature,
    jd_text: Annotated[str, Form()],
    resume_file: Annotated[UploadFile | None, File()] = None,
) -> JSONResponse:
    # Validate JD length
    if not jd_text or len(jd_text.strip()) < 50:
        raise HTTPException(
            status_code=400,
            detail="Please paste a job description (at least 50 characters).",
        )

    # Validate resume presence for features that need it
    if feature in _RESUME_REQUIRED and resume_file is None:
        raise HTTPException(
            status_code=400,
            detail="This feature needs both a resume and a job description. Please upload your resume.",
        )

    resume_text: str | None = None

    if resume_file is not None:
        file_bytes = await resume_file.read()

        if len(file_bytes) > MAX_UPLOAD_BYTES:
            raise HTTPException(
                status_code=413,
                detail=f"File exceeds the {MAX_UPLOAD_BYTES // (1024 * 1024)} MB limit.",
            )

        try:
            resume_text = extract_resume_text(file_bytes, resume_file.filename or "")
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    system_prompt, temperature = FEATURE_CONFIG[feature.value]
    user_content = build_user_content(resume_text, jd_text)

    try:
        output = generate(system_prompt, user_content, temperature=temperature)
    except LLMError:
        raise HTTPException(
            status_code=502,
            detail="We couldn't reach the AI service. Please try again in a moment.",
        )

    return JSONResponse({"output": output})
```

- [ ] **Step 4: Run tests and confirm they pass**

```bash
pytest tests/test_generate_router.py -v
```

Expected: All 6 tests PASS

- [ ] **Step 5: Commit**

```bash
git add app/routers/generate.py tests/test_generate_router.py
git commit -m "feat: add generate router with input validation and feature routing"
```

---

## Task 8: Export router

**Files:**
- Create: `app/routers/export.py`
- Create: `tests/test_export_router.py`

- [ ] **Step 1: Write failing tests**

```python
# tests/test_export_router.py
import pytest
from unittest.mock import patch
from fastapi.testclient import TestClient


@pytest.fixture
def client():
    with patch("app.config.GEMINI_API_KEY", "test-key"):
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
    assert "passwd" not in cd
    # Should fall back to hireprep_output or sanitized form
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
```

- [ ] **Step 2: Run tests to confirm they fail**

```bash
pytest tests/test_export_router.py -v 2>&1 | head -20
```

- [ ] **Step 3: Write `app/routers/export.py`**

```python
import re
from enum import Enum

from fastapi import APIRouter
from fastapi.responses import Response
from pydantic import BaseModel

from app.doc_generator import to_pdf, to_docx


router = APIRouter()


class ExportFormat(str, Enum):
    pdf = "pdf"
    docx = "docx"


class ExportRequest(BaseModel):
    content: str
    filename: str


_SAFE_FILENAME = re.compile(r"[^A-Za-z0-9_\-]")


def _sanitize_filename(name: str) -> str:
    """Strip unsafe characters from a filename; fall back to hireprep_output."""
    safe = _SAFE_FILENAME.sub("", name)
    return safe if safe else "hireprep_output"


@router.post("/api/export/{format}")
async def export_document(format: ExportFormat, body: ExportRequest) -> Response:
    safe_name = _sanitize_filename(body.filename)

    if format == ExportFormat.pdf:
        data = to_pdf(body.content, safe_name)
        return Response(
            content=data,
            media_type="application/pdf",
            headers={"Content-Disposition": f'attachment; filename="{safe_name}.pdf"'},
        )

    # docx
    data = to_docx(body.content, safe_name)
    return Response(
        content=data,
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        headers={"Content-Disposition": f'attachment; filename="{safe_name}.docx"'},
    )
```

- [ ] **Step 4: Run all tests**

```bash
pytest tests/ -v
```

Expected: All tests PASS

- [ ] **Step 5: Commit**

```bash
git add app/routers/export.py tests/test_export_router.py
git commit -m "feat: add export router for PDF and DOCX download"
```

---

## Task 9: Main FastAPI app

**Files:**
- Create: `app/main.py`

- [ ] **Step 1: Write `app/main.py`**

```python
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from app.config import MAX_UPLOAD_BYTES, validate_config
from app.routers import generate, export

# Fail fast if GEMINI_API_KEY is not configured
validate_config()

app = FastAPI(title="hireprep.ai")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:8000", "http://127.0.0.1:8000"],
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

app.include_router(generate.router)
app.include_router(export.router)

_STATIC_DIR = Path(__file__).parent.parent / "static"
_INDEX_HTML = _STATIC_DIR / "index.html"


@app.middleware("http")
async def enforce_upload_size(request: Request, call_next):
    """Reject requests whose Content-Length exceeds the upload limit."""
    content_length = request.headers.get("content-length")
    if content_length and int(content_length) > MAX_UPLOAD_BYTES:
        return JSONResponse(
            status_code=413,
            content={"detail": f"File exceeds the {MAX_UPLOAD_BYTES // (1024 * 1024)} MB limit."},
        )
    return await call_next(request)


@app.get("/", response_class=HTMLResponse)
async def index():
    return _INDEX_HTML.read_text(encoding="utf-8")


# Mount static assets — must come after explicit routes
app.mount("/", StaticFiles(directory=str(_STATIC_DIR)), name="static")
```

- [ ] **Step 2: Run all tests to confirm nothing broke**

```bash
pytest tests/ -v
```

- [ ] **Step 3: Commit**

```bash
git add app/main.py
git commit -m "feat: wire FastAPI app with CORS, size limit middleware, and static serving"
```

---

## Task 10: SVG assets

**Files:**
- Create: `static/assets/logo.svg`
- Create: `static/favicon.svg`

- [ ] **Step 1: Create `static/assets/logo.svg`**

```xml
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 180 36" fill="none">
  <!-- Mark: stacked offset squares suggesting layered documents -->
  <rect x="3" y="9" width="22" height="22" rx="6" fill="#6E7F8D"/>
  <rect x="9" y="3" width="22" height="22" rx="6" fill="#2C3640"/>
  <!-- Wordmark -->
  <text x="42" y="24" font-family="Inter, -apple-system, sans-serif" font-weight="600" font-size="18" fill="#2C3640" letter-spacing="-0.02em">hireprep<tspan fill="#6E7F8D" font-weight="400">.ai</tspan></text>
</svg>
```

- [ ] **Step 2: Create `static/favicon.svg`**

```xml
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 32 32" fill="none">
  <rect x="2" y="10" width="20" height="20" rx="5" fill="#6E7F8D"/>
  <rect x="10" y="2" width="20" height="20" rx="5" fill="#2C3640"/>
</svg>
```

- [ ] **Step 3: Commit**

```bash
git add static/assets/logo.svg static/favicon.svg
git commit -m "feat: add logo and favicon SVG assets"
```

---

## Task 11: Frontend HTML

**Files:**
- Create: `static/index.html`

- [ ] **Step 1: Create `static/index.html`**

```html
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>hireprep.ai — Job Application Prep</title>
  <link rel="icon" href="/favicon.svg" type="image/svg+xml" />
  <link rel="preconnect" href="https://fonts.googleapis.com" />
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin />
  <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600&display=swap" rel="stylesheet" />
  <link rel="stylesheet" href="/css/styles.css" />
</head>
<body>

  <!-- ==================== HEADER ==================== -->
  <header class="site-header">
    <div class="header-inner">
      <a href="/" class="logo-link" aria-label="hireprep.ai home">
        <img src="/assets/logo.svg" alt="hireprep.ai" class="logo" width="140" height="28" />
      </a>
    </div>
  </header>

  <!-- ==================== MAIN ==================== -->
  <main>

    <!-- Hero -->
    <section class="hero">
      <p class="eyebrow">AI-POWERED JOB APPLICATION PREP</p>
      <h1>Prepare for your next role.</h1>
      <p class="subheading">Upload your resume and paste a job description. Generate a cover letter, practice questions, and a tailored resume in seconds.</p>
    </section>

    <!-- Inputs -->
    <section class="inputs-section" aria-label="Inputs">
      <div class="inputs-grid">

        <!-- Resume upload card -->
        <div class="card input-card" id="resume-card">
          <label class="input-label" for="resume-file-input">Your resume</label>
          <div
            class="drop-zone"
            id="drop-zone"
            role="button"
            tabindex="0"
            aria-label="Upload resume — click or drag and drop"
          >
            <!-- Icon: document with arrow -->
            <svg class="drop-icon" xmlns="http://www.w3.org/2000/svg" width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
              <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/>
              <polyline points="14 2 14 8 20 8"/>
              <line x1="12" y1="12" x2="12" y2="18"/>
              <polyline points="9 15 12 18 15 15"/>
            </svg>
            <p class="drop-primary">Drop your resume here</p>
            <p class="drop-secondary">or <span class="drop-link">click to browse</span></p>
            <p class="drop-hint">.pdf or .docx, up to 5 MB</p>
          </div>
          <input type="file" id="resume-file-input" accept=".pdf,.docx,.doc" aria-hidden="true" tabindex="-1" />

          <!-- File preview (shown after upload) -->
          <div class="file-preview hidden" id="file-preview" role="status">
            <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
              <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/>
              <polyline points="14 2 14 8 20 8"/>
            </svg>
            <div class="file-info">
              <span class="file-name" id="file-name"></span>
              <span class="file-size" id="file-size"></span>
            </div>
            <button class="file-remove" id="file-remove" aria-label="Remove resume">
              <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
                <line x1="18" y1="6" x2="6" y2="18"/>
                <line x1="6" y1="6" x2="18" y2="18"/>
              </svg>
            </button>
          </div>
        </div>

        <!-- Job description card -->
        <div class="card input-card" id="jd-card">
          <label class="input-label" for="jd-textarea">Job description</label>
          <div class="textarea-wrapper">
            <textarea
              id="jd-textarea"
              class="jd-textarea"
              placeholder="Paste the job description here..."
              rows="12"
              spellcheck="true"
              aria-label="Job description"
            ></textarea>
            <span class="char-count" id="char-count" aria-live="polite">0 characters</span>
          </div>
        </div>

      </div>
    </section>

    <!-- Action cards -->
    <section class="actions-section" aria-label="Generate actions">
      <div class="actions-grid">

        <button class="card action-card" data-feature="cover_letter" aria-label="Generate cover letter">
          <div class="action-icon-wrap">
            <!-- Pencil / writing icon -->
            <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
              <path d="M17 3a2.828 2.828 0 1 1 4 4L7.5 20.5 2 22l1.5-5.5L17 3z"/>
            </svg>
          </div>
          <div class="action-text">
            <span class="action-title">Cover letter</span>
            <span class="action-desc">A personalized cover letter tailored to this role.</span>
          </div>
          <!-- Spinner (hidden by default) -->
          <svg class="spinner hidden" xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true">
            <circle cx="12" cy="12" r="10" stroke-opacity="0.2"/>
            <path d="M12 2a10 10 0 0 1 10 10" class="spinner-arc"/>
          </svg>
        </button>

        <button class="card action-card" data-feature="practice_questions" aria-label="Generate practice questions">
          <div class="action-icon-wrap">
            <!-- Chat bubbles / questions icon -->
            <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
              <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/>
            </svg>
          </div>
          <div class="action-text">
            <span class="action-title">Practice questions</span>
            <span class="action-desc">Realistic interview questions for this role. Works with just a job description.</span>
          </div>
          <svg class="spinner hidden" xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true">
            <circle cx="12" cy="12" r="10" stroke-opacity="0.2"/>
            <path d="M12 2a10 10 0 0 1 10 10" class="spinner-arc"/>
          </svg>
        </button>

        <button class="card action-card" data-feature="resume_questions" aria-label="Generate resume-specific questions">
          <div class="action-icon-wrap">
            <!-- User search / magnifier icon -->
            <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
              <circle cx="11" cy="11" r="8"/>
              <line x1="21" y1="21" x2="16.65" y2="16.65"/>
              <line x1="11" y1="8" x2="11" y2="14"/>
              <line x1="8" y1="11" x2="14" y2="11"/>
            </svg>
          </div>
          <div class="action-text">
            <span class="action-title">Resume questions</span>
            <span class="action-desc">Questions an interviewer would likely ask based on your resume.</span>
          </div>
          <svg class="spinner hidden" xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true">
            <circle cx="12" cy="12" r="10" stroke-opacity="0.2"/>
            <path d="M12 2a10 10 0 0 1 10 10" class="spinner-arc"/>
          </svg>
        </button>

        <button class="card action-card" data-feature="tailored_resume" aria-label="Generate tailored resume">
          <div class="action-icon-wrap">
            <!-- List / resume icon -->
            <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
              <line x1="8" y1="6" x2="21" y2="6"/>
              <line x1="8" y1="12" x2="21" y2="12"/>
              <line x1="8" y1="18" x2="21" y2="18"/>
              <line x1="3" y1="6" x2="3.01" y2="6"/>
              <line x1="3" y1="12" x2="3.01" y2="12"/>
              <line x1="3" y1="18" x2="3.01" y2="18"/>
            </svg>
          </div>
          <div class="action-text">
            <span class="action-title">Tailored resume</span>
            <span class="action-desc">Your resume rewritten to emphasize the most relevant experience.</span>
          </div>
          <svg class="spinner hidden" xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true">
            <circle cx="12" cy="12" r="10" stroke-opacity="0.2"/>
            <path d="M12 2a10 10 0 0 1 10 10" class="spinner-arc"/>
          </svg>
        </button>

      </div>
    </section>

    <!-- Output section (hidden until first generation) -->
    <section class="output-section hidden" id="output-section" aria-label="Generated output" aria-live="polite">
      <div class="card output-card">
        <div class="output-header">
          <h2 class="output-title" id="output-title">Output</h2>
          <div class="output-toolbar" role="toolbar" aria-label="Output actions">
            <button class="tool-btn" id="btn-copy" aria-label="Copy to clipboard">
              <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
                <rect x="9" y="9" width="13" height="13" rx="2" ry="2"/>
                <path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"/>
              </svg>
              <span id="copy-label">Copy</span>
            </button>
            <button class="tool-btn" id="btn-download-pdf" aria-label="Download as PDF">
              <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
                <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/>
                <polyline points="7 10 12 15 17 10"/>
                <line x1="12" y1="15" x2="12" y2="3"/>
              </svg>
              PDF
            </button>
            <button class="tool-btn" id="btn-download-docx" aria-label="Download as DOCX">
              <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
                <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/>
                <polyline points="7 10 12 15 17 10"/>
                <line x1="12" y1="15" x2="12" y2="3"/>
              </svg>
              DOCX
            </button>
            <button class="tool-btn" id="btn-regenerate" aria-label="Regenerate">
              <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
                <polyline points="23 4 23 10 17 10"/>
                <path d="M20.49 15a9 9 0 1 1-2.12-9.36L23 10"/>
              </svg>
              Regenerate
            </button>
            <button class="tool-btn tool-btn--close" id="btn-close-output" aria-label="Close output">
              <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
                <line x1="18" y1="6" x2="6" y2="18"/>
                <line x1="6" y1="6" x2="18" y2="18"/>
              </svg>
            </button>
          </div>
        </div>
        <!-- Skeleton pulse (shown during loading) -->
        <div class="output-skeleton hidden" id="output-skeleton" aria-hidden="true">
          <div class="skeleton-line" style="width:85%"></div>
          <div class="skeleton-line" style="width:70%"></div>
          <div class="skeleton-line" style="width:90%"></div>
          <div class="skeleton-line" style="width:60%"></div>
          <div class="skeleton-line" style="width:80%"></div>
        </div>
        <pre class="output-text" id="output-text" tabindex="0"></pre>
      </div>
    </section>

  </main>

  <!-- ==================== FOOTER ==================== -->
  <footer class="site-footer">
    <p>hireprep.ai &copy; <span id="footer-year"></span></p>
  </footer>

  <!-- ==================== ERROR MODAL ==================== -->
  <div class="modal-backdrop hidden" id="modal-backdrop" role="dialog" aria-modal="true" aria-labelledby="modal-title" aria-describedby="modal-message">
    <div class="modal-card">
      <div class="modal-icon-wrap" aria-hidden="true">
        <!-- Warning triangle -->
        <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round">
          <path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"/>
          <line x1="12" y1="9" x2="12" y2="13"/>
          <line x1="12" y1="17" x2="12.01" y2="17"/>
        </svg>
      </div>
      <h2 class="modal-title" id="modal-title">Something's missing</h2>
      <p class="modal-message" id="modal-message"></p>
      <button class="btn-primary" id="modal-close">Got it</button>
    </div>
  </div>

  <script src="/js/app.js"></script>
</body>
</html>
```

- [ ] **Step 2: Commit**

```bash
git add static/index.html
git commit -m "feat: add single-page HTML with all structural sections and components"
```

---

## Task 12: CSS styles

**Files:**
- Create: `static/css/styles.css`

- [ ] **Step 1: Create `static/css/styles.css`**

```css
/* ============================================================
   Design tokens
   ============================================================ */
:root {
  --bg:             #FAFBFF;
  --surface:        #EFF2F9;
  --surface-2:      #E4EBF1;
  --border:         #D8DEE6;
  --muted:          #B5BFC6;
  --text-secondary: #6E7F8D;
  --text-primary:   #2C3640;
  --accent:         #3A4A56;
  --accent-hover:   #2C3640;
  --danger:         #C44A4A;
  --success:        #4A8C5F;
  --shadow-light:   #FFFFFF;
  --shadow-dark:    rgba(22, 27, 29, 0.12);

  --shadow-card:
    -5px -5px 10px var(--shadow-light),
     5px  5px 10px var(--shadow-dark);
  --shadow-card-hover:
    -8px -8px 16px var(--shadow-light),
     8px  8px 16px var(--shadow-dark);
  --shadow-inset:
    inset -3px -3px 6px var(--shadow-light),
    inset  3px  3px 6px var(--shadow-dark);

  --radius-card:   16px;
  --radius-btn:    12px;
  --radius-input:  12px;
}

/* ============================================================
   Reset & base
   ============================================================ */
*, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }

html {
  font-size: 15px;
  -webkit-font-smoothing: antialiased;
}

body {
  font-family: "Inter", -apple-system, BlinkMacSystemFont, sans-serif;
  background: var(--bg);
  color: var(--text-primary);
  line-height: 1.55;
  min-height: 100vh;
  display: flex;
  flex-direction: column;
}

main { flex: 1; }

/* ============================================================
   Utility
   ============================================================ */
.hidden { display: none !important; }

/* ============================================================
   Header
   ============================================================ */
.site-header {
  position: sticky;
  top: 0;
  z-index: 100;
  background: var(--bg);
  border-bottom: 1px solid var(--border);
  padding: 0 32px;
}

.header-inner {
  max-width: 960px;
  margin: 0 auto;
  height: 56px;
  display: flex;
  align-items: center;
}

.logo-link { display: inline-flex; align-items: center; text-decoration: none; }
.logo { height: 28px; width: auto; }

/* ============================================================
   Hero
   ============================================================ */
.hero {
  max-width: 960px;
  margin: 64px auto 0;
  padding: 0 32px;
  text-align: center;
}

.eyebrow {
  font-size: 11px;
  font-weight: 600;
  letter-spacing: 0.12em;
  color: var(--text-secondary);
  margin-bottom: 16px;
}

h1 {
  font-size: 2.4rem;
  font-weight: 600;
  letter-spacing: -0.01em;
  color: var(--text-primary);
  margin-bottom: 16px;
}

.subheading {
  font-size: 1rem;
  color: var(--text-secondary);
  max-width: 540px;
  margin: 0 auto;
  line-height: 1.6;
}

/* ============================================================
   Card base
   ============================================================ */
.card {
  background: var(--surface);
  border-radius: var(--radius-card);
  box-shadow: var(--shadow-card);
  padding: 24px;
}

/* ============================================================
   Input section
   ============================================================ */
.inputs-section {
  max-width: 960px;
  margin: 48px auto 0;
  padding: 0 32px;
}

.inputs-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 24px;
}

.input-card { display: flex; flex-direction: column; gap: 12px; }

.input-label {
  font-size: 0.85rem;
  font-weight: 600;
  color: var(--text-secondary);
  letter-spacing: 0.02em;
  text-transform: uppercase;
}

/* Drop zone */
.drop-zone {
  border: 2px dashed var(--border);
  border-radius: var(--radius-input);
  padding: 32px 16px;
  text-align: center;
  cursor: pointer;
  transition: border-color 0.15s, background 0.15s;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 6px;
  background: var(--bg);
}

.drop-zone:hover, .drop-zone:focus {
  border-color: var(--accent);
  outline: none;
}

.drop-zone.drag-over {
  border-color: var(--accent);
  border-style: solid;
  background: var(--surface-2);
}

.drop-icon { color: var(--muted); margin-bottom: 4px; }
.drop-primary { font-weight: 500; font-size: 0.95rem; color: var(--text-primary); }
.drop-secondary { font-size: 0.85rem; color: var(--text-secondary); }
.drop-link { color: var(--accent); font-weight: 500; }
.drop-hint { font-size: 0.78rem; color: var(--muted); margin-top: 4px; }

#resume-file-input { position: absolute; width: 0; height: 0; opacity: 0; pointer-events: none; }

/* File preview */
.file-preview {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px 12px;
  background: var(--surface-2);
  border-radius: var(--radius-input);
  box-shadow: var(--shadow-inset);
  color: var(--text-secondary);
}

.file-info { display: flex; flex-direction: column; flex: 1; min-width: 0; }
.file-name { font-weight: 500; font-size: 0.9rem; color: var(--text-primary); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.file-size { font-size: 0.78rem; color: var(--muted); }

.file-remove {
  background: none;
  border: none;
  cursor: pointer;
  color: var(--muted);
  padding: 4px;
  border-radius: 6px;
  display: flex;
  align-items: center;
  transition: color 0.15s;
}
.file-remove:hover { color: var(--danger); }

/* Job description textarea */
.textarea-wrapper { position: relative; display: flex; flex-direction: column; flex: 1; }

.jd-textarea {
  width: 100%;
  min-height: 240px;
  max-height: 400px;
  padding: 14px;
  font-family: inherit;
  font-size: 0.9rem;
  line-height: 1.55;
  color: var(--text-primary);
  background: var(--surface-2);
  border: 1.5px solid var(--border);
  border-radius: var(--radius-input);
  box-shadow: var(--shadow-inset);
  resize: vertical;
  outline: none;
  transition: border-color 0.15s;
}

.jd-textarea::placeholder { color: var(--muted); }
.jd-textarea:focus { border-color: var(--accent); }

.char-count {
  position: absolute;
  bottom: 10px;
  right: 12px;
  font-size: 0.72rem;
  color: var(--muted);
  pointer-events: none;
}

/* ============================================================
   Actions section
   ============================================================ */
.actions-section {
  max-width: 960px;
  margin: 32px auto 0;
  padding: 0 32px;
}

.actions-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 16px;
}

.action-card {
  display: flex;
  align-items: center;
  gap: 16px;
  padding: 20px 24px;
  cursor: pointer;
  border: none;
  text-align: left;
  transition: box-shadow 0.18s, opacity 0.18s;
  position: relative;
  overflow: hidden;
}

.action-card:hover {
  box-shadow: var(--shadow-card-hover);
}

.action-card:active {
  box-shadow: var(--shadow-inset);
}

.action-card.loading {
  pointer-events: none;
}

.action-card.dimmed {
  opacity: 0.4;
  pointer-events: none;
}

.action-icon-wrap {
  flex-shrink: 0;
  width: 40px;
  height: 40px;
  background: var(--surface-2);
  border-radius: 10px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--accent);
  box-shadow: var(--shadow-inset);
}

.action-text {
  display: flex;
  flex-direction: column;
  gap: 3px;
  flex: 1;
  min-width: 0;
}

.action-title {
  font-weight: 600;
  font-size: 0.95rem;
  color: var(--text-primary);
}

.action-desc {
  font-size: 0.82rem;
  color: var(--text-secondary);
  line-height: 1.4;
}

/* Spinner */
.spinner {
  flex-shrink: 0;
  animation: spin 0.8s linear infinite;
  color: var(--accent);
}

.spinner-arc {
  stroke-dasharray: 30;
  stroke-dashoffset: 0;
  stroke-linecap: round;
}

@keyframes spin {
  from { transform: rotate(0deg); }
  to   { transform: rotate(360deg); }
}

/* ============================================================
   Output section
   ============================================================ */
.output-section {
  max-width: 960px;
  margin: 32px auto 48px;
  padding: 0 32px;
}

.output-card { padding: 0; }

.output-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 20px 24px 0;
  gap: 16px;
  flex-wrap: wrap;
}

.output-title {
  font-size: 1rem;
  font-weight: 600;
  color: var(--text-primary);
}

.output-toolbar {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}

.tool-btn {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 7px 12px;
  font-family: inherit;
  font-size: 0.82rem;
  font-weight: 500;
  color: var(--text-secondary);
  background: var(--surface-2);
  border: 1px solid var(--border);
  border-radius: var(--radius-btn);
  cursor: pointer;
  transition: color 0.15s, background 0.15s, box-shadow 0.15s;
}

.tool-btn:hover {
  color: var(--text-primary);
  background: var(--surface);
  box-shadow: var(--shadow-card);
}

.tool-btn--close {
  margin-left: 4px;
  padding: 7px 9px;
}

.tool-btn--close:hover { color: var(--danger); }

/* Skeleton */
.output-skeleton {
  padding: 24px;
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.skeleton-line {
  height: 14px;
  background: var(--surface-2);
  border-radius: 6px;
  animation: pulse 1.4s ease-in-out infinite;
}

@keyframes pulse {
  0%, 100% { opacity: 1; }
  50%       { opacity: 0.45; }
}

/* Output text */
.output-text {
  padding: 24px;
  font-family: "Inter", sans-serif;
  font-size: 0.88rem;
  line-height: 1.65;
  color: var(--text-primary);
  white-space: pre-wrap;
  word-break: break-word;
  overflow-wrap: anywhere;
  max-height: 600px;
  overflow-y: auto;
  border-top: 1px solid var(--border);
  margin-top: 16px;
  outline: none;
}

/* ============================================================
   Footer
   ============================================================ */
.site-footer {
  padding: 24px 32px;
  text-align: center;
  font-size: 0.78rem;
  color: var(--muted);
  border-top: 1px solid var(--border);
}

/* ============================================================
   Modal
   ============================================================ */
.modal-backdrop {
  position: fixed;
  inset: 0;
  z-index: 200;
  display: flex;
  align-items: center;
  justify-content: center;
  background: rgba(46, 58, 68, 0.15);
  backdrop-filter: blur(6px);
  -webkit-backdrop-filter: blur(6px);
  padding: 24px;
}

.modal-card {
  background: var(--surface);
  border-radius: var(--radius-card);
  box-shadow: var(--shadow-card-hover);
  padding: 32px;
  max-width: 400px;
  width: 100%;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 16px;
  text-align: center;
}

.modal-icon-wrap {
  width: 48px;
  height: 48px;
  background: var(--surface-2);
  border-radius: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--danger);
  box-shadow: var(--shadow-inset);
}

.modal-title {
  font-size: 1rem;
  font-weight: 600;
  color: var(--text-primary);
}

.modal-message {
  font-size: 0.88rem;
  color: var(--text-secondary);
  line-height: 1.55;
}

.btn-primary {
  padding: 10px 28px;
  font-family: inherit;
  font-size: 0.9rem;
  font-weight: 600;
  color: #fff;
  background: var(--accent);
  border: none;
  border-radius: var(--radius-btn);
  cursor: pointer;
  transition: background 0.15s;
}

.btn-primary:hover { background: var(--accent-hover); }

/* ============================================================
   Responsive
   ============================================================ */
@media (max-width: 720px) {
  h1 { font-size: 1.8rem; }

  .inputs-grid,
  .actions-grid {
    grid-template-columns: 1fr;
  }

  .site-header { padding: 0 16px; }
  .hero,
  .inputs-section,
  .actions-section,
  .output-section { padding: 0 16px; }

  .hero { margin-top: 40px; }
}

@media (max-width: 480px) {
  .output-toolbar { gap: 6px; }
  .tool-btn { padding: 6px 10px; font-size: 0.78rem; }
}
```

- [ ] **Step 2: Commit**

```bash
git add static/css/styles.css
git commit -m "feat: add complete CSS with neumorphic design system"
```

---

## Task 13: Frontend JavaScript

**Files:**
- Create: `static/js/app.js`

- [ ] **Step 1: Create `static/js/app.js`**

```javascript
/**
 * app.js — hireprep.ai frontend
 *
 * All UI state lives in `appState`. No localStorage, no sessionStorage.
 * Page refresh = clean slate.
 */

// ============================================================
// State
// ============================================================

const appState = {
  resumeFile: null,         // File object | null
  resumeText: null,         // not used client-side, but tracks presence
  jdText: "",
  currentFeature: null,     // last triggered feature key
  currentOutput: null,      // last generated text
  isLoading: false,
};

// Feature metadata
const FEATURES = {
  cover_letter:        { title: "Your cover letter",          filename: "cover_letter" },
  practice_questions:  { title: "Practice questions",         filename: "practice_questions" },
  resume_questions:    { title: "Resume-specific questions",  filename: "resume_questions" },
  tailored_resume:     { title: "Your tailored resume",       filename: "tailored_resume" },
};

// ============================================================
// DOM refs
// ============================================================

const dropZone        = document.getElementById("drop-zone");
const fileInput       = document.getElementById("resume-file-input");
const filePreview     = document.getElementById("file-preview");
const dropZoneWrap    = document.getElementById("resume-card");
const fileName        = document.getElementById("file-name");
const fileSize        = document.getElementById("file-size");
const fileRemove      = document.getElementById("file-remove");
const jdTextarea      = document.getElementById("jd-textarea");
const charCount       = document.getElementById("char-count");
const actionCards     = document.querySelectorAll(".action-card");
const outputSection   = document.getElementById("output-section");
const outputTitle     = document.getElementById("output-title");
const outputText      = document.getElementById("output-text");
const outputSkeleton  = document.getElementById("output-skeleton");
const btnCopy         = document.getElementById("btn-copy");
const copyLabel       = document.getElementById("copy-label");
const btnDownloadPdf  = document.getElementById("btn-download-pdf");
const btnDownloadDocx = document.getElementById("btn-download-docx");
const btnRegenerate   = document.getElementById("btn-regenerate");
const btnCloseOutput  = document.getElementById("btn-close-output");
const modalBackdrop   = document.getElementById("modal-backdrop");
const modalTitle      = document.getElementById("modal-title");
const modalMessage    = document.getElementById("modal-message");
const modalClose      = document.getElementById("modal-close");
const footerYear      = document.getElementById("footer-year");

// ============================================================
// Init
// ============================================================

footerYear.textContent = new Date().getFullYear();

// ============================================================
// Drop zone — file upload
// ============================================================

const MAX_FILE_BYTES = 5 * 1024 * 1024;
const ALLOWED_EXTS   = new Set([".pdf", ".docx", ".doc"]);

dropZone.addEventListener("click", () => fileInput.click());
dropZone.addEventListener("keydown", (e) => {
  if (e.key === "Enter" || e.key === " ") { e.preventDefault(); fileInput.click(); }
});

dropZone.addEventListener("dragover", (e) => {
  e.preventDefault();
  dropZone.classList.add("drag-over");
});

dropZone.addEventListener("dragleave", () => {
  dropZone.classList.remove("drag-over");
});

dropZone.addEventListener("drop", (e) => {
  e.preventDefault();
  dropZone.classList.remove("drag-over");
  const file = e.dataTransfer?.files?.[0];
  if (file) handleFileSelected(file);
});

fileInput.addEventListener("change", () => {
  const file = fileInput.files?.[0];
  if (file) handleFileSelected(file);
  // Reset input so the same file can be re-selected after removal
  fileInput.value = "";
});

fileRemove.addEventListener("click", clearResume);

function handleFileSelected(file) {
  const ext = "." + file.name.split(".").pop().toLowerCase();

  if (!ALLOWED_EXTS.has(ext)) {
    showModal("Invalid file type", "That file format isn't supported. Please upload a .pdf or .docx file.");
    return;
  }

  if (file.size > MAX_FILE_BYTES) {
    showModal("File too large", "Files must be 5 MB or smaller.");
    return;
  }

  appState.resumeFile = file;
  fileName.textContent = file.name;
  fileSize.textContent = formatBytes(file.size);
  dropZone.classList.add("hidden");
  filePreview.classList.remove("hidden");
}

function clearResume() {
  appState.resumeFile = null;
  filePreview.classList.add("hidden");
  dropZone.classList.remove("hidden");
}

function formatBytes(bytes) {
  if (bytes < 1024) return bytes + " B";
  if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + " KB";
  return (bytes / (1024 * 1024)).toFixed(1) + " MB";
}

// ============================================================
// JD textarea — live character count + auto-resize
// ============================================================

jdTextarea.addEventListener("input", () => {
  appState.jdText = jdTextarea.value;
  const n = jdTextarea.value.length;
  charCount.textContent = n === 1 ? "1 character" : `${n.toLocaleString()} characters`;

  // Auto-resize (capped by CSS max-height)
  jdTextarea.style.height = "auto";
  jdTextarea.style.height = jdTextarea.scrollHeight + "px";
});

// ============================================================
// Action cards
// ============================================================

actionCards.forEach((card) => {
  card.addEventListener("click", () => {
    const feature = card.dataset.feature;
    triggerFeature(feature, card);
  });
});

async function triggerFeature(feature, triggerCard) {
  if (appState.isLoading) return;

  const jd = jdTextarea.value.trim();
  const hasResume = Boolean(appState.resumeFile);
  const needsResume = feature !== "practice_questions";

  // Client-side validation
  if (!hasResume && !jd) {
    showModal("Missing inputs", "This feature needs both a resume and a job description. Please upload your resume and paste the job description.");
    return;
  }
  if (needsResume && !hasResume) {
    showModal("Missing resume", "Please upload your resume to use this feature.");
    return;
  }
  if (!jd) {
    showModal("Missing job description", "Please paste a job description to use this feature.");
    return;
  }

  appState.currentFeature = feature;
  setLoading(true, triggerCard);
  showOutputSkeleton(feature);

  try {
    const formData = new FormData();
    formData.append("jd_text", jd);
    if (appState.resumeFile) formData.append("resume_file", appState.resumeFile);

    const res = await fetch(`/api/generate/${feature}`, {
      method: "POST",
      body: formData,
    });

    if (!res.ok) {
      const body = await res.json().catch(() => ({ detail: "An unexpected error occurred." }));
      throw new Error(body.detail || "An unexpected error occurred.");
    }

    const data = await res.json();
    appState.currentOutput = data.output;
    renderOutput(feature, data.output);
  } catch (err) {
    hideOutputSkeleton();
    showModal("Error", err.message);
  } finally {
    setLoading(false, triggerCard);
  }
}

// ============================================================
// Loading state
// ============================================================

function setLoading(loading, activeCard) {
  appState.isLoading = loading;
  actionCards.forEach((card) => {
    const spinner = card.querySelector(".spinner");
    const iconWrap = card.querySelector(".action-icon-wrap");
    if (card === activeCard) {
      if (loading) {
        card.classList.add("loading");
        spinner?.classList.remove("hidden");
        iconWrap?.classList.add("hidden");
      } else {
        card.classList.remove("loading");
        spinner?.classList.add("hidden");
        iconWrap?.classList.remove("hidden");
      }
    } else {
      card.classList.toggle("dimmed", loading);
    }
  });
}

// ============================================================
// Output rendering
// ============================================================

function showOutputSkeleton(feature) {
  outputSection.classList.remove("hidden");
  outputTitle.textContent = FEATURES[feature]?.title ?? "Output";
  outputText.classList.add("hidden");
  outputSkeleton.classList.remove("hidden");
  outputSection.scrollIntoView({ behavior: "smooth", block: "start" });
}

function hideOutputSkeleton() {
  outputSkeleton.classList.add("hidden");
  outputText.classList.remove("hidden");
}

function renderOutput(feature, text) {
  outputTitle.textContent = FEATURES[feature]?.title ?? "Output";
  outputText.textContent = text;
  outputSkeleton.classList.add("hidden");
  outputText.classList.remove("hidden");
  outputSection.scrollIntoView({ behavior: "smooth", block: "start" });
}

btnCloseOutput.addEventListener("click", () => {
  outputSection.classList.add("hidden");
  appState.currentOutput = null;
  appState.currentFeature = null;
});

btnRegenerate.addEventListener("click", () => {
  if (!appState.currentFeature || appState.isLoading) return;
  const card = document.querySelector(`[data-feature="${appState.currentFeature}"]`);
  triggerFeature(appState.currentFeature, card);
});

// ============================================================
// Copy
// ============================================================

btnCopy.addEventListener("click", async () => {
  if (!appState.currentOutput) return;
  try {
    await navigator.clipboard.writeText(appState.currentOutput);
    copyLabel.textContent = "Copied";
    btnCopy.querySelector("svg").style.stroke = "var(--success)";
    setTimeout(() => {
      copyLabel.textContent = "Copy";
      btnCopy.querySelector("svg").style.stroke = "";
    }, 1500);
  } catch {
    showModal("Copy failed", "Your browser blocked clipboard access. Please select the text and copy manually.");
  }
});

// ============================================================
// Download
// ============================================================

async function downloadOutput(format) {
  if (!appState.currentOutput || !appState.currentFeature) return;
  const filename = FEATURES[appState.currentFeature]?.filename ?? "hireprep_output";

  try {
    const res = await fetch(`/api/export/${format}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ content: appState.currentOutput, filename }),
    });

    if (!res.ok) throw new Error("Export failed. Please try again.");

    const blob = await res.blob();
    const url  = URL.createObjectURL(blob);
    const a    = document.createElement("a");
    a.href     = url;
    a.download = `${filename}.${format}`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  } catch (err) {
    showModal("Download failed", err.message);
  }
}

btnDownloadPdf.addEventListener("click",  () => downloadOutput("pdf"));
btnDownloadDocx.addEventListener("click", () => downloadOutput("docx"));

// ============================================================
// Modal
// ============================================================

function showModal(title, message) {
  modalTitle.textContent   = title;
  modalMessage.textContent = message;
  modalBackdrop.classList.remove("hidden");
  modalClose.focus();
}

function closeModal() {
  modalBackdrop.classList.add("hidden");
}

modalClose.addEventListener("click", closeModal);
modalBackdrop.addEventListener("click", (e) => {
  if (e.target === modalBackdrop) closeModal();
});

document.addEventListener("keydown", (e) => {
  if (e.key === "Escape" && !modalBackdrop.classList.contains("hidden")) {
    closeModal();
  }
});
```

- [ ] **Step 2: Commit**

```bash
git add static/js/app.js
git commit -m "feat: add complete vanilla JS frontend with state management and API integration"
```

---

## Task 14: README and PROJECT_DOCS

**Files:**
- Create: `README.md`
- Create: `PROJECT_DOCS.md`

- [ ] **Step 1: Create `README.md`**

```markdown
# hireprep.ai

A web app that helps job seekers prepare application materials using AI. Upload your resume and a job description to generate a cover letter, practice interview questions, resume-specific questions, and a tailored resume.

## Prerequisites

- Python 3.14.3
- A [Google Gemini API key](https://aistudio.google.com/app/apikey)

## Setup

```bash
cp .env.example .env
# Edit .env and paste your GEMINI_API_KEY
```

## Run

```bash
bash run.sh
```

Open [http://127.0.0.1:8000](http://127.0.0.1:8000).

For full architecture and design decisions, see [PROJECT_DOCS.md](PROJECT_DOCS.md).
```

- [ ] **Step 2: Create `PROJECT_DOCS.md`** (see detailed spec — write comprehensive 1800–2500 word document covering architecture, request lifecycle, file-by-file tour, system prompts, safety notes, extension points, known limitations, and dependency list)

- [ ] **Step 3: Commit**

```bash
git add README.md PROJECT_DOCS.md
git commit -m "docs: add README and PROJECT_DOCS with full architecture documentation"
```

---

## Task 15: Smoke test and verification

- [ ] **Step 1: Run the full test suite**

```bash
source .venv/bin/activate && pytest tests/ -v
```

Expected: all tests pass

- [ ] **Step 2: Start the server (requires `.env` with real GEMINI_API_KEY)**

```bash
bash run.sh
```

Expected: Uvicorn starts on `http://127.0.0.1:8000`

- [ ] **Step 3: Open browser and verify checklist**

- [ ] Page loads, no console errors
- [ ] Logo renders in header
- [ ] Resume drop zone works (drag and drop + click-to-browse)
- [ ] `.doc` upload shows friendly error modal
- [ ] File >5 MB shows size error modal
- [ ] JD character count updates live
- [ ] "Cover letter" without resume shows missing-resume modal
- [ ] "Practice questions" without resume and with JD proceeds to generate
- [ ] Each of the four features generates output end-to-end
- [ ] Copy button works and reverts after 1.5s
- [ ] Download PDF opens in PDF viewer
- [ ] Download DOCX opens in Word/Pages
- [ ] Regenerate re-runs the same feature
- [ ] Close output button hides the output section
- [ ] Page refresh clears all state
- [ ] Responsive at 640px viewport width

- [ ] **Step 4: Final commit**

```bash
git add .
git commit -m "chore: final verification pass — production ready"
```

---

## Self-Review: Spec Coverage

| Spec section | Covered in task |
|---|---|
| §1 Four features, no auto-run | Task 13 (JS), Task 7 (router guard) |
| §1 Copy + download outputs | Task 13 (JS), Task 8 (router) |
| §1 Ephemeral session | Task 13 (no localStorage) |
| §2 Python 3.14.3 + exact stack | Task 1 (requirements.txt) |
| §3 Exact directory structure | All tasks |
| §4.1 CORS + 5MB limit + static | Task 9 (main.py) |
| §4.2 fail-fast API key | Task 2 (config.py) |
| §4.3 PDF/DOCX/DOC handling | Task 3 (parser) |
| §4.4 Gemini client + LLMError | Task 4 (llm_client) |
| §4.5 Four prompts verbatim | Task 5 (prompts.py) |
| §4.6 PDF + DOCX generation | Task 6 (doc_generator) |
| §4.7 Generate router validation | Task 7 |
| §4.8 Export router + sanitize | Task 8 |
| §5.1 Exact CSS design tokens | Task 12 (styles.css) |
| §5.2 Full HTML structure | Task 11 (index.html) |
| §5.3 All JS interactions | Task 13 (app.js) |
| §5.4 Error modal + all messages | Task 11 + 13 |
| §5.5 Loading states | Task 13 |
| §6 Logo + favicon SVGs | Task 10 |
| §7 run.sh + README | Task 1 + 14 |
| §8 PROJECT_DOCS.md | Task 14 |
| §9 Quality checklist | Task 15 |
