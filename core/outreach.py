"""Draft outreach emails for job applications. Draft-only — never auto-sent."""
import json

from core.llm_logger import tracked_call

DRAFT_EMAIL_PROMPT = """You are drafting a job application outreach email for a candidate to
send themselves. This is a DRAFT ONLY that the candidate will review and edit before sending —
never auto-sent.

CANDIDATE NAME: {candidate_name}

CANDIDATE CV (structured):
{cv_structured}

JOB: {job_title} at {job_company}
JOB DETAILS (structured, may include a contact name, department, or reporting line if the
posting stated one):
{job_structured}

WHY THIS IS A GOOD FIT (from an earlier match assessment against this candidate's real CV):
{match_reasons}

{greeting_hint}

Write a concise, professional outreach email with a subject line and body.
Rules:
- Ground every claim about the candidate in the CV data above — never invent skills,
  achievements, or experience not present there.
- Never invent facts about the company beyond what's in the job details.
- Do not fabricate personal knowledge of, or history with, the company that isn't grounded in
  the job posting.
- Keep the body under 200 words.
- Sign off with the candidate's real name given above.

Return only this JSON object, no explanation, no markdown fences:
{{
  "subject": "...",
  "body": "..."
}}"""


def draft_email(
    cv_structured: dict,
    job_structured: dict,
    job_title: str,
    job_company: str,
    match_result: dict,
    candidate_name: str,
) -> dict:
    """Draft a personalised outreach email. Returns {subject, body}."""
    contact_name = job_structured.get("contact_name")
    if contact_name:
        greeting_hint = f'Address the email to "{contact_name}" by name.'
    else:
        greeting_hint = (
            "No contact name is known — use a generic professional greeting "
            '(e.g. "Hi there," or "To the hiring team,"), never invent a name.'
        )

    message = tracked_call(
        prompt_type="outreach_email",
        model="claude-haiku-4-5-20251001",
        max_tokens=768,
        messages=[{
            "role": "user",
            "content": DRAFT_EMAIL_PROMPT.format(
                candidate_name=candidate_name,
                cv_structured=json.dumps(cv_structured, indent=2),
                job_title=job_title,
                job_company=job_company,
                job_structured=json.dumps(job_structured, indent=2),
                match_reasons=json.dumps(match_result.get("reasons", []), indent=2),
                greeting_hint=greeting_hint,
            ),
        }],
    )
    return _parse_json_response(message)


DRAFT_LINKEDIN_PROMPT = """You are drafting a LinkedIn connection request note for a candidate to
send themselves. This is a DRAFT ONLY that the candidate will review and edit before sending —
never auto-sent.

LinkedIn connection request notes have a HARD LIMIT of 300 characters, including spaces. This is
a real platform constraint, not a style preference — the message must fit within it, or LinkedIn
will reject it.

CANDIDATE NAME: {candidate_name}

CANDIDATE CV (structured):
{cv_structured}

JOB: {job_title} at {job_company}
JOB DETAILS (structured, may include a contact name if the posting stated one):
{job_structured}

WHY THIS IS A GOOD FIT (from an earlier match assessment against this candidate's real CV):
{match_reasons}

{greeting_hint}

Write a single short connection-request message.
Rules:
- Stay at or under 300 characters total, including spaces.
- Ground every claim about the candidate in the CV data above — never invent skills,
  achievements, or experience not present there.
- Never invent facts about the company beyond what's in the job details.
- Do not include a sign-off or the candidate's name at the end — LinkedIn already shows the
  sender's identity, so spend the character budget on substance instead.

Return only this JSON object, no explanation, no markdown fences:
{{
  "message": "..."
}}"""


def draft_linkedin_message(
    cv_structured: dict,
    job_structured: dict,
    job_title: str,
    job_company: str,
    match_result: dict,
    candidate_name: str,
) -> dict:
    """Draft a LinkedIn connection request note. Returns {message, character_count}."""
    contact_name = job_structured.get("contact_name")
    if contact_name:
        greeting_hint = f'Address it to "{contact_name}" by name if there is room.'
    else:
        greeting_hint = "No contact name is known — never invent one."

    message = tracked_call(
        prompt_type="outreach_linkedin",
        model="claude-haiku-4-5-20251001",
        max_tokens=256,
        messages=[{
            "role": "user",
            "content": DRAFT_LINKEDIN_PROMPT.format(
                candidate_name=candidate_name,
                cv_structured=json.dumps(cv_structured, indent=2),
                job_title=job_title,
                job_company=job_company,
                job_structured=json.dumps(job_structured, indent=2),
                match_reasons=json.dumps(match_result.get("reasons", []), indent=2),
                greeting_hint=greeting_hint,
            ),
        }],
    )
    result = _parse_json_response(message)
    # Compute the character count ourselves rather than trust the model's word
    # for whether it actually honoured the 300-char limit.
    result["character_count"] = len(result["message"])
    return result


def _parse_json_response(message) -> dict:
    raw = message.content[0].text.strip()
    if raw.startswith("```"):
        lines = raw.splitlines()
        raw = "\n".join(lines[1:-1]).strip()
    return json.loads(raw)
