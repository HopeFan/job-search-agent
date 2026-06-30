"""Extract structured fields from a raw job description via Claude."""
import json
import re

from core.llm_logger import tracked_call

EXTRACTION_PROMPT = """Extract the following fields from this job description as a JSON object.
Only include what is explicitly stated. Use null for anything not mentioned.

Fields to extract:
- required_skills: list of strings — skills/technologies explicitly required
- preferred_skills: list of strings — skills listed as nice-to-have or preferred
- seniority: string — one of: "junior", "mid", "senior", "lead", "principal", or null
- work_arrangement: string — one of: "on-site", "hybrid", "remote", or null
- visa_sponsorship: boolean or null — true if sponsorship is offered, false if not, null if not mentioned
- salary_min: number or null — minimum salary if stated (in AUD, per year)
- salary_max: number or null — maximum salary if stated (in AUD, per year)

Return only valid JSON. No explanation, no markdown fences.

Job description:
{description}"""


def strip_html(html: str) -> str:
    """Remove HTML tags and collapse whitespace."""
    text = re.sub(r"<[^>]+>", " ", html)
    return re.sub(r"\s+", " ", text).strip()


def extract_job_structured(description: str) -> dict:
    """Strip HTML, send to Claude, return structured dict."""
    clean = strip_html(description)
    message = tracked_call(
        prompt_type="job_extraction",
        model="claude-haiku-4-5-20251001",
        max_tokens=1024,
        messages=[
            {"role": "user", "content": EXTRACTION_PROMPT.format(description=clean)}
        ],
    )
    raw = message.content[0].text.strip()
    if raw.startswith("```"):
        lines = raw.splitlines()
        raw = "\n".join(lines[1:-1]).strip()
    return json.loads(raw)
