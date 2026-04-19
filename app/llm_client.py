from google import genai
from google.genai import types as genai_types

from app.config import GEMINI_API_KEY, GEMINI_MODEL


class LLMError(Exception):
    """Raised when the Gemini API call fails."""


# Create client once at module load — reused across all requests
_client = genai.Client(api_key=GEMINI_API_KEY)


def generate(
    system_prompt: str,
    user_content: str,
    temperature: float = 0.7,
) -> str:
    """Call Gemini and return the response text.

    Raises LLMError on any API failure so callers can convert to HTTP 502.
    """
    config = genai_types.GenerateContentConfig(
        system_instruction=system_prompt,
        temperature=temperature,
    )

    try:
        response = _client.models.generate_content(
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
