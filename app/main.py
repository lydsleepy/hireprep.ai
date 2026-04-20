from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from app.config import MAX_UPLOAD_BYTES, validate_config
from app.routers import generate, export

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
    content_length = request.headers.get("content-length")
    if content_length and int(content_length) > MAX_UPLOAD_BYTES:
        return JSONResponse(
            status_code=413,
            content={"detail": f"File exceeds the {MAX_UPLOAD_BYTES // (1024 * 1024)} MB limit."},
        )
    return await call_next(request)


@app.get("/", response_class=HTMLResponse)
async def index():
    if _INDEX_HTML.exists():
        return _INDEX_HTML.read_text(encoding="utf-8")
    return HTMLResponse("<h1>hireprep.ai</h1>")


# Only mount static if dir exists (it may not during tests)
if _STATIC_DIR.exists():
    app.mount("/", StaticFiles(directory=str(_STATIC_DIR)), name="static")
