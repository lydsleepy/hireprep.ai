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
