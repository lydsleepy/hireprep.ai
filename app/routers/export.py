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
