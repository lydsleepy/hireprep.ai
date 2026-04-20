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
