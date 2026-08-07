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

4. GAP CHECK — For each of the job's required_skills that does NOT already appear in the
   candidate's skills list: search the candidate's work_history descriptions and summary
   for real evidence they've actually done this, even if it wasn't listed as a skill.
   - Only mark "buried" if the evidence specifically demonstrates that exact skill or a direct
     equivalent — not just adjacent or related work in the same general area. When in doubt,
     mark "missing" instead.
   - If you find real evidence, mark it "buried" and quote the specific evidence from the CV.
   - If you find no evidence, mark it "missing" — do not invent a bridge.
   Skip any required_skill that's already in the candidate's skills list; only report the
   ones that are absent from that list.

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
- gap_suggestions.evidence must be a real quote or close paraphrase from work_history — never fabricated.
  If status is "missing", evidence and suggestion must both be null.

Return only this JSON object, no explanation, no markdown fences:
{{
  "band": "strong" | "moderate" | "weak",
  "reasons": ["reason 1", "reason 2", "reason 3"],
  "is_stretch": true | false,
  "stretch_gap": "description of the gap" | null,
  "gap_suggestions": [
    {{
      "skill": "the required skill",
      "status": "buried" | "missing",
      "evidence": "quote/paraphrase from work_history" | null,
      "suggestion": "what to add/surface, grounded in the evidence" | null
    }}
  ]
}}"""


def rate_job(cv_structured: dict, job_structured: dict, job_title: str, job_company: str) -> dict:
    """Rate one job against the CV. Returns band, reasons, is_stretch, stretch_gap."""
    message = tracked_call(
        prompt_type="matcher",
        model="claude-haiku-4-5-20251001",
        max_tokens=1536,
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
    result = json.loads(raw)

    # Enforce the honesty line in code, not just in the prompt: a "missing" skill
    # must never carry evidence or a suggestion, even if the model drifts.
    for gap in result.get("gap_suggestions", []):
        if gap.get("status") == "missing":
            gap["evidence"] = None
            gap["suggestion"] = None

    return result
