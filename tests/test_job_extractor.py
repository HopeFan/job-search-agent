from unittest.mock import MagicMock, patch

from core.job_extractor import extract_job_structured, strip_html


def test_strip_html_removes_tags_and_collapses_whitespace():
    html = "<p>Hello   <b>world</b></p>\n\n<div>!</div>"
    assert strip_html(html) == "Hello world !"


def _fake_llm_response(json_text):
    message = MagicMock()
    message.content = [MagicMock(text=json_text)]
    return message


@patch("core.job_extractor.tracked_call")
def test_extract_job_structured_keeps_contact_email_present_in_text(mock_call):
    mock_call.return_value = _fake_llm_response(
        '{"required_skills": [], "preferred_skills": [], "seniority": null, '
        '"work_arrangement": null, "visa_sponsorship": null, "salary_min": null, '
        '"salary_max": null, "contact_name": "Jane Smith", '
        '"contact_email": "jane@company.com", "reports_to": null, "department": null}'
    )
    description = "Apply by emailing jane@company.com, attention Jane Smith."
    result = extract_job_structured(description)
    assert result["contact_email"] == "jane@company.com"
    assert result["contact_name"] == "Jane Smith"


@patch("core.job_extractor.tracked_call")
def test_extract_job_structured_nulls_fabricated_contact_email(mock_call):
    # Model claims an email that never appears in the source text — must be
    # treated as fabricated and nulled, regardless of the prompt instruction.
    mock_call.return_value = _fake_llm_response(
        '{"required_skills": [], "preferred_skills": [], "seniority": null, '
        '"work_arrangement": null, "visa_sponsorship": null, "salary_min": null, '
        '"salary_max": null, "contact_name": null, '
        '"contact_email": "made-up@nowhere.com", "reports_to": null, "department": null}'
    )
    description = "We are hiring a data engineer to join our team."
    result = extract_job_structured(description)
    assert result["contact_email"] is None


@patch("core.job_extractor.tracked_call")
def test_extract_job_structured_keeps_reports_to_and_department_present_in_text(mock_call):
    mock_call.return_value = _fake_llm_response(
        '{"required_skills": [], "preferred_skills": [], "seniority": null, '
        '"work_arrangement": null, "visa_sponsorship": null, "salary_min": null, '
        '"salary_max": null, "contact_name": null, "contact_email": null, '
        '"reports_to": "Head of Data Engineering", "department": "Platform Engineering"}'
    )
    description = "This role reports to the Head of Data Engineering within Platform Engineering."
    result = extract_job_structured(description)
    assert result["reports_to"] == "Head of Data Engineering"
    assert result["department"] == "Platform Engineering"
