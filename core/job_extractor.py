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
- contact_name: string or null — a named person to contact, only if a name is given
- contact_email: string or null — an email address, only if literally printed in the text
- reports_to: string or null — the role/title this position reports to (e.g. "Head of Data
  Engineering"), only if explicitly stated
- department: string or null — the team or department this role sits within, only if stated

Return only valid JSON. No explanation, no markdown fences.

Job description:
{description}"""

CONTACT_FIELDS = ["contact_name", "contact_email", "reports_to", "department"]


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
    result = json.loads(raw)

    # Enforce the honesty line in code, not just the prompt: a claimed contact
    # detail must literally appear in the source text, or it's treated as
    # fabricated and nulled out. Same pattern as the matcher's gap suggestions —
    # prompt instructions alone aren't reliable across repeated calls.
    clean_lower = clean.lower()
    for field in CONTACT_FIELDS:
        value = result.get(field)
        if value and str(value).lower() not in clean_lower:
            result[field] = None

    return result
