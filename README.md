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
