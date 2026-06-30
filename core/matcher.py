"""Match a job against a candidate CV using an LLM rubric."""
import json

from core.llm_logger import tracked_call

RUBRIC_PROMPT = """You are evaluating whether a job is a good fit for a candidate.

CANDIDATE CV (structured):
{cv_structured}

JOB (structured):
{job_structured}

JOB TITLE: {job_title}
COMPANY: {job_company}

Evaluate the fit using this rubric:

1. SKILLS COVERAGE — How many of the job's required_skills appear in the candidate's skills?
   Are there any hard blockers (required skills the candidate clearly has no experience with)?

2. SENIORITY FIT — Does the job's seniority level match the candidate's years of experience
   and most recent title?

3. WORK ARRANGEMENT — Does the job's work_arrangement (hybrid/remote/on-site) seem
   acceptable given the candidate's background and location?

Assign ONE band:
- "strong"   : good skills coverage, right seniority, no hard blockers
- "moderate" : some gaps but manageable, or slight mismatch on one dimension
- "weak"     : major skills gaps or significantly wrong seniority — still worth showing as a stretch

Rules:
- NEVER output a percentage or numeric score
- Be honest about gaps — do not inflate the band to be encouraging
- If the band is "moderate" or "weak" but the candidate has the core skills and could grow into it,
  set is_stretch to true and name the specific gap in stretch_gap
- Reasons must be grounded in the actual data above — do not invent skills the candidate doesn't have

Return only this JSON object, no explanation, no markdown fences:
{{
  "band": "strong" | "moderate" | "weak",
  "reasons": ["reason 1", "reason 2", "reason 3"],
  "is_stretch": true | false,
  "stretch_gap": "description of the gap" | null
}}"""


def rate_job(cv_structured: dict, job_structured: dict, job_title: str, job_company: str) -> dict:
    """Rate one job against the CV. Returns band, reasons, is_stretch, stretch_gap."""
    message = tracked_call(
        prompt_type="matcher",
        model="claude-haiku-4-5-20251001",
        max_tokens=1024,
        messages=[{
            "role": "user",
            "content": RUBRIC_PROMPT.format(
                cv_structured=json.dumps(cv_structured, indent=2),
                job_structured=json.dumps(job_structured, indent=2),
                job_title=job_title,
                job_company=job_company,
            ),
        }],
    )
    raw = message.content[0].text.strip()
    if raw.startswith("```"):
        lines = raw.splitlines()
        raw = "\n".join(lines[1:-1]).strip()
    return json.loads(raw)
