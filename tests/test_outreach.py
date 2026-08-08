from unittest.mock import MagicMock, patch

from core.outreach import draft_email

CV = {"summary": "Data engineer with 7 years experience.", "skills": ["Python", "SQL"]}
MATCH_RESULT = {"reasons": ["Strong Python and SQL skills match the role."]}


def _fake_llm_response(json_text):
    message = MagicMock()
    message.content = [MagicMock(text=json_text)]
    return message


@patch("core.outreach.tracked_call")
def test_draft_email_returns_subject_and_body(mock_call):
    mock_call.return_value = _fake_llm_response(
        '{"subject": "Application for Data Engineer", "body": "Hi there, ..."}'
    )
    result = draft_email(CV, {}, "Data Engineer", "Acme Co", MATCH_RESULT, "Erfan Hesami")
    assert result == {"subject": "Application for Data Engineer", "body": "Hi there, ..."}


@patch("core.outreach.tracked_call")
def test_draft_email_strips_markdown_fences(mock_call):
    mock_call.return_value = _fake_llm_response(
        '```json\n{"subject": "Hello", "body": "Body text"}\n```'
    )
    result = draft_email(CV, {}, "Data Engineer", "Acme Co", MATCH_RESULT, "Erfan Hesami")
    assert result == {"subject": "Hello", "body": "Body text"}


@patch("core.outreach.tracked_call")
def test_draft_email_instructs_named_greeting_when_contact_known(mock_call):
    mock_call.return_value = _fake_llm_response('{"subject": "s", "body": "b"}')
    job_structured = {"contact_name": "Leanne O'Connor"}
    draft_email(CV, job_structured, "Data Engineer", "Acme Co", MATCH_RESULT, "Erfan Hesami")

    prompt = mock_call.call_args.kwargs["messages"][0]["content"]
    assert 'Address the email to "Leanne O\'Connor" by name.' in prompt


@patch("core.outreach.tracked_call")
def test_draft_email_instructs_generic_greeting_when_no_contact(mock_call):
    mock_call.return_value = _fake_llm_response('{"subject": "s", "body": "b"}')
    draft_email(CV, {}, "Data Engineer", "Acme Co", MATCH_RESULT, "Erfan Hesami")

    prompt = mock_call.call_args.kwargs["messages"][0]["content"]
    assert "No contact name is known" in prompt
    assert "never invent a name" in prompt
