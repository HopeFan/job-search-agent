"""CV extraction — plain text from .docx, then structured JSON via Claude."""
import json
from pathlib import Path

from docx import Document

from core.llm_logger import tracked_call

EXTRACTION_PROMPT = """Extract the following fields from this CV as a JSON object.
Be accurate — only include what is actually written in the CV. Do not invent or infer.

Fields to extract:
- current_title: string — the most recent job title
- years_experience: number — total years of professional experience (best estimate)
- skills: list of strings — all technical and domain skills mentioned
- work_history: list of objects with keys: company, title, start, end, description
- education: list of objects with keys: institution, degree, field, year
- summary: string — a 2-3 sentence summary of the candidate's profile

Return only valid JSON. No explanation, no markdown fences.

CV text:
{cv_text}"""


def extract_text(docx_path: str | Path) -> str:
    """Return all paragraph text from a .docx file joined by newlines."""
    doc = Document(str(docx_path))
    return "\n".join(p.text for p in doc.paragraphs if p.text.strip())


def extract_structured(cv_text: str) -> dict:
    """Send CV text to Claude and return a structured dict."""
    message = tracked_call(
        prompt_type="cv_extraction",
        model="claude-haiku-4-5-20251001",
        max_tokens=2048,
        messages=[
            {"role": "user", "content": EXTRACTION_PROMPT.format(cv_text=cv_text)}
        ],
    )
    raw = message.content[0].text.strip()

    # Strip markdown code fences if Claude added them despite instructions
    if raw.startswith("```"):
        lines = raw.splitlines()
        raw = "\n".join(lines[1:-1]).strip()

    return json.loads(raw)
