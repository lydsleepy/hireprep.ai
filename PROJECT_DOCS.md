# PROJECT_DOCS.md — hireprep.ai

## 1. What hireprep.ai is

hireprep.ai is a single-page web application that helps job seekers prepare application materials for a specific role. The user uploads their resume (PDF or DOCX) and pastes a job description into a text area, then clicks one of four action buttons: Cover Letter, Practice Questions, Resume Questions, or Tailored Resume. Each click sends the inputs to a FastAPI backend, which constructs a prompt and calls the Google Gemini API; the AI-generated text is returned as JSON and displayed inline in an output panel below the action buttons. From the output panel the user can copy the text to the clipboard, download it as a PDF, download it as a DOCX, or regenerate the output with one click. The application is intentionally ephemeral: no files, text, or generated content are stored on the server at any point, and a page refresh returns the browser to a completely blank state.


## 2. Architecture overview

```
                         +-------------------+
                         |    Browser        |
                         |  static/index.html|
                         |  static/js/app.js |
                         +--------+----------+
                                  |
                    HTTP POST (multipart or JSON)
                                  |
                         +--------v----------+
                         |   FastAPI         |
                         |   app/main.py     |
                         |                   |
                +--------+----+   +----------+--------+
                |  generate   |   |   export          |
                |  router     |   |   router          |
                | (generate.py)|  | (export.py)       |
                +--------+----+   +----------+--------+
                         |                   |
              +-----------+         +---------+--------+
              |                     |                  |
     +--------v-------+    +--------v------+  +--------v------+
     | resume_parser  |    | llm_client.py |  | doc_generator |
     | (pypdf/docx)   |    | (Gemini API)  |  | (reportlab/   |
     +----------------+    +---------------+  |  python-docx) |
                                              +---------------+
```

The architecture has three tiers. The browser tier is a plain HTML/CSS/JavaScript single-page application — no framework, no build step. The application tier is a FastAPI server that handles routing, input validation, text extraction, and prompt assembly. The external service tier is the Google Gemini API, which is the only network dependency beyond the browser itself.


## 3. Request lifecycle walkthrough

Here is exactly what happens when a user clicks the "Cover Letter" action card.

The click event fires on the `<button class="action-card" data-feature="cover_letter">` element. The `actionCards.forEach` listener in `app.js` reads `card.dataset.feature` and calls `triggerFeature("cover_letter", card)`. That function checks `appState.resumeFile` and `jdTextarea.value`; because cover letter requires a resume (`needsResume` is true for everything except `practice_questions`), it shows a modal and returns early if either input is missing. No network request is made until both are present.

Once validation passes, the function builds a `FormData` object containing `jd_text` and `resume_file`, then calls `fetch("/api/generate/cover_letter", { method: "POST", body: formData })`. `setLoading(true, card)` adds a spinner to the active card and dims the other three while the request is in flight.

FastAPI receives the multipart form. The path parameter `cover_letter` is validated against the `Feature` enum; FastAPI injects `jd_text` as a form field and `resume_file` as an `UploadFile`. The router checks that `jd_text` is at least 50 characters and that a resume file was supplied (required because `cover_letter` is in `_RESUME_REQUIRED`). It reads the file bytes and calls `extract_resume_text(file_bytes, filename)`, which routes to the PDF or DOCX parser and returns cleaned plain text.

The router then calls `build_user_content(resume_text, jd_text)`, which wraps both inputs in `[RESUME]` and `[JOB DESCRIPTION]` labeled blocks. It retrieves `(COVER_LETTER_PROMPT, 0.7)` from `FEATURE_CONFIG` and calls `llm_client.generate(system_prompt, user_content, temperature=0.7)`. The singleton `genai.Client` sends the request to Gemini; any SDK exception is caught and re-raised as `LLMError`, which the router maps to HTTP 502.

The response text is stripped and returned as `JSONResponse({"output": "..."})`. Back in the browser, `app.js` stores the text in `appState.currentOutput` and calls `renderOutput("cover_letter", text)`, which puts the text into the `<pre id="output-text">` element, hides the skeleton loader, and scrolls the output panel into view.


## 4. File-by-file tour

**`app/config.py`** loads environment variables via `python-dotenv` and defines module-level constants: `GEMINI_API_KEY`, `GEMINI_MODEL` (currently `gemini-2.5-flash`), `MAX_UPLOAD_BYTES` (5 MB), and the sets of allowed extensions and MIME types. The `validate_config()` function raises a `RuntimeError` at startup if `GEMINI_API_KEY` is empty, so the server refuses to start rather than failing at the point of the first Gemini call with a less obvious error.

**`app/llm_client.py`** creates a single `genai.Client` at module load time and reuses it across all requests. The public `generate()` function wraps all Gemini SDK exceptions in `LLMError`, a lightweight custom exception that routers catch and convert to HTTP 502 without exposing internal stack traces. The `temperature` parameter defaults to 0.7 and can be overridden per feature.

**`app/resume_parser.py`** exposes `extract_resume_text(file_bytes, filename)`, which dispatches on file extension: `.doc` is rejected immediately, `.pdf` is handled by `pypdf.PdfReader`, and `.docx` by `python-docx`. The DOCX path iterates both paragraphs and table cells because many resume templates use tables for multi-column layout; skipping tables would silently drop large sections of content. After extraction, `_require_min_text()` rejects files where fewer than 100 characters were recovered — the typical result from a scanned, image-only PDF.

**`app/doc_generator.py`** provides `to_pdf(text, title)` and `to_docx(text, title)`, both returning raw bytes rather than writing to disk. This keeps the export path stateless and lets the bytes stream directly into the HTTP response. The PDF renderer splits on double newlines into paragraphs, preserves internal newlines as `<br/>` tags, and escapes XML special characters before handing off to `reportlab`. The DOCX renderer bolds any line that is entirely uppercase or ends with a colon, preserving resume section header formatting.

**`app/prompts.py`** defines the four system prompt constants, `FEATURE_CONFIG` (a dict mapping each feature key to a `(prompt, temperature)` tuple), and `build_user_content()`. The tailored resume temperature is 0.4 rather than 0.7 because precision matters more than variety for a document editing task. `build_user_content()` accepts `resume_text` as `str | None`; when it is `None`, only the `[JOB DESCRIPTION]` block is sent, enabling JD-only mode for practice questions.

**`app/routers/generate.py`** exposes `POST /api/generate/{feature}`. FastAPI validates the path parameter against the `Feature` enum (a 422 is returned for unknown values) and injects `jd_text` and `resume_file` from the multipart body. The router validates inputs in order — JD length, resume presence, file size, and text extraction — and maps `ValueError` to HTTP 400 and `LLMError` to HTTP 502 with user-facing messages.

**`app/routers/export.py`** exposes `POST /api/export/{format}`. The `_sanitize_filename()` function strips every character outside an alphanumeric-underscore-hyphen allowlist before using the name in the `Content-Disposition` header, preventing path traversal or header injection from a crafted filename.

**`app/main.py`** calls `validate_config()` before the application object is created, restricts CORS to localhost origins, and adds an HTTP middleware layer that enforces the upload size limit before any router runs. The `index` route serves `static/index.html`; the `StaticFiles` mount serves CSS, JS, and other assets.

**`static/index.html`** is the only HTML page. Every interactive element has a stable `id` consumed by `app.js`. No JavaScript framework is used; the page is valid standalone HTML with no build step.

**`static/css/styles.css`** defines a neumorphic shadow system using three CSS custom properties — `--shadow-card`, `--shadow-card-hover`, and `--shadow-inset` — each composed of a white top-left highlight and a dark bottom-right shadow. All visual tokens live in the `:root` block. A single responsive breakpoint at 768px collapses the two-column input grid to one column.

**`static/js/app.js`** is organized around a single `appState` object (`resumeFile`, `jdText`, `currentFeature`, `currentOutput`, `isLoading`). All state mutations go through `appState` rather than reading from the DOM. No `localStorage` or `sessionStorage` is used — the application is intentionally single-session, and browser storage would raise privacy questions without meaningful benefit. `setLoading()` disables all action cards during a request to prevent concurrent submissions from overwriting `appState.currentOutput`.


## 5. The four system prompts

**COVER_LETTER_PROMPT** specifies a 280–380 word range and a four-part structure. Its hard rules ban fabricating employers, metrics, or titles, and also ban emotional openers like "I've always admired your company" unless the resume actually supports that claim — a common model failure mode. The banned clichés list ("thrilled to apply," "leveraging," "proven track record," etc.) is explicit because models default to these phrases under pressure to produce polished prose; naming them specifically suppresses them reliably.

**PRACTICE_QUESTIONS_PROMPT** prescribes a question mix across four categories (behavioral, technical, background, situational) and instructs the model to tailor three or four questions to the resume when one is provided. The instruction to keep tailored questions "realistic, not overly specific gotchas" prevents questions that would only make sense to a hiring manager who had already spoken to the candidate. The ban on including answers or coaching is there because doing so would defeat the purpose of practice.

**RESUME_QUESTIONS_PROMPT** limits the model strictly to content present in the resume — transitions, gaps, skills listed without project evidence, and quantified claims that might warrant follow-up. The model would otherwise extrapolate and invent plausible-sounding questions about things the candidate never claimed. The tone directive ("curious, not adversarial") prevents the output from reading as skeptical, which would discourage rather than help the user.

**TAILORED_RESUME_PROMPT** uses the most emphatic language of the four, prefacing hard rules with "these take absolute precedence." It enumerates specific data types that must not be added or inflated (employers, dates, degrees, metrics, team sizes), then separately lists what is permitted (reordering, rewriting verb forms, trimming less-relevant content, incorporating JD keywords where truthfully applicable). The explicit "You may" section gives the model a clear, bounded scope for editing rather than leaving it to guess how much latitude it has.


## 6. Safety and governance notes

**Fabrication prevention.** Each prompt repeats "never add" and "never inflate" rather than relying on a single general instruction. A broad "don't make things up" directive is easily overridden by the goal of producing compelling output; naming specific prohibited data types (employer names, metric values, dates, team sizes) is harder for the model to rationalize around.

**Resume-JD mismatch.** The application does not score or warn about mismatch. If a user submits a resume with no relevant overlap to the job description, the model will still produce output — it will simply be thin. The output quality itself serves as the signal.

**Ephemeral session privacy.** Nothing is written to disk, a database, or a cache. File bytes are read into memory, processed, and discarded within the request. A server breach exposes no user data beyond what is currently being processed in active request memory.

**Why .doc output is not offered.** `python-docx` can read legacy `.doc` binary files but does not write them. The Word 97-2003 binary format is undocumented; supporting it as an output format would require a separate library with a much larger dependency surface. DOCX is the correct target for any newly generated document.

**Why there is no scoring or ranking.** LLM-based scoring reflects training data distribution and prompt wording, not a consistent or auditable rubric. Offering a match score would invite users to treat it as an objective hiring signal, which it cannot be, and would expose the application to algorithmic bias claims.

**How practice_questions JD-only mode works.** Three features — `cover_letter`, `resume_questions`, and `tailored_resume` — are in the `_RESUME_REQUIRED` set in `generate.py`. `practice_questions` is not. When no resume is submitted for that feature, `resume_text` is `None`, `build_user_content(None, jd_text)` omits the `[RESUME]` block, and the prompt instructs the model to tailor questions to the resume "if provided," so the output degrades gracefully to generic JD-based questions.


## 7. Extension points

**Adding a new feature** requires changes in four places: add a member to the `Feature` enum in `generate.py`; add it to `_RESUME_REQUIRED` if a resume is needed; add a `(prompt, temperature)` entry to `FEATURE_CONFIG` in `prompts.py`; add an `<button class="action-card" data-feature="...">` in `index.html` and a matching entry in the `FEATURES` object in `app.js`. No other changes are needed.

**Swapping the LLM provider** only requires rewriting `llm_client.py`. The module's public interface is a single `generate(system_prompt, user_content, temperature)` function that returns a string or raises `LLMError`. Nothing outside this module imports provider-specific types, so replacing the Gemini SDK with OpenAI, Anthropic, or a local model has no cascade effect.

**Adding persistence** would involve assigning each browser session a UUID cookie, storing outputs in a database keyed by session ID and feature, and exposing a retrieval route. FastAPI's dependency injection is well-suited for this: a `get_db()` dependency injected into route functions provides a database session without changing the route signatures meaningfully.

**Adding authentication** can be done through FastAPI's dependency injection by adding a `current_user: User = Depends(get_current_user)` parameter to any route that should be gated. Combined with persistence, this would let users return to previously generated materials.


## 8. Known limitations

**Scanned PDFs.** `pypdf` only reads a PDF's text layer. Scanned documents contain no text layer, so the parser raises a `ValueError` when fewer than 100 characters are extracted. There is no OCR fallback; the user must re-upload a text-based file.

**Legacy .doc upload.** Files with a `.doc` extension are rejected at the `extract_resume_text` boundary. `python-docx` reading support for `.doc` is unreliable enough that a hard rejection with a clear message is better than silent partial extraction.

**Gemini rate limits.** Free-tier quotas return 429 responses from the API. `llm_client.py` catches these as generic exceptions and raises `LLMError`, which surfaces as "We couldn't reach the AI service." There is no automatic retry or backoff.

**Context window size.** Very long inputs may exceed Gemini's context limit. The 5 MB upload ceiling constrains file size but does not guarantee extracted text fits within the model's context; oversized requests surface as a generic 502 error.

**No response streaming.** The full Gemini response is buffered before returning JSON to the browser. The user sees the skeleton loader for the entire generation time; the panel transitions directly from skeleton to complete text with no incremental display.


## 9. Dependency list

**fastapi** — web framework handling routing, request parsing, dependency injection, and parameter validation.

**uvicorn[standard]** — ASGI server that runs the FastAPI app; the `[standard]` extra adds the `uvloop` event loop and `httptools` parser.

**python-dotenv** — reads `.env` and injects key-value pairs into the process environment before `os.getenv` is called.

**python-multipart** — enables FastAPI to parse `multipart/form-data` bodies (the encoding for file + text field submissions).

**google-genai** — the official Google Generative AI Python SDK, used in `llm_client.py` to call the Gemini API.

**pypdf** — reads the text layer of PDF files; used in `resume_parser.py` for `.pdf` resume uploads.

**python-docx** — reads and writes DOCX (Office Open XML); used in `resume_parser.py` for extraction and in `doc_generator.py` for export.

**reportlab** — PDF generation library used in `doc_generator.py` to render plain text into a paginated PDF with correct margins.

**pydantic** — provides `BaseModel` for the `ExportRequest` schema in `export.py`; also used internally by FastAPI for all validation.

**httpx** — async HTTP client used by FastAPI's `TestClient` in the test suite.

**pytest** — test runner for the `tests/` directory.

**pytest-asyncio** — extends pytest with `async def` test function support, needed for testing async route handlers.
