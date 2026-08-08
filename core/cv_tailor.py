"""Apply targeted text edits to a CV .docx while preserving formatting.

A paragraph is only editable if every run inside it shares the same
formatting (bold/italic/size/color) — Word often splits a paragraph into
several runs purely from spell-check/autocorrect boundaries, with no real
visual difference between them. Paragraphs with genuinely mixed formatting
(e.g. a bold title followed by a plain date) are left untouched.
"""
import json

from core.llm_logger import tracked_call

PICK_CATEGORY_PROMPT = """A candidate's CV lists skills grouped under these existing categories:
{categories}

A buried skill was found with real evidence in the candidate's CV, but it isn't
listed under any category yet:

SKILL: {skill}
EVIDENCE: {evidence}

Which existing category is the single best fit for this skill? Only pick one if
it's a genuine match — do not force a fit into an unrelated category.

Return only this JSON object, no explanation, no markdown fences:
{{
  "category": "<one of the categories above, exactly as written>" | null
}}"""


def pick_target_category(categories: list[str], skill: str, evidence: str) -> str | None:
    """Ask the LLM which existing skills-table category a buried skill belongs in.

    Returns None if no category is a genuine fit. v1 never invents a new
    category or table row — only an existing category, verbatim, is accepted.
    """
    message = tracked_call(
        prompt_type="cv_tailor_category",
        model="claude-haiku-4-5-20251001",
        max_tokens=256,
        messages=[{
            "role": "user",
            "content": PICK_CATEGORY_PROMPT.format(
                categories="\n".join(f"- {c}" for c in categories),
                skill=skill,
                evidence=evidence,
            ),
        }],
    )
    raw = message.content[0].text.strip()
    if raw.startswith("```"):
        lines = raw.splitlines()
        raw = "\n".join(lines[1:-1]).strip()
    category = json.loads(raw).get("category")

    # Enforce in code: the model must return one of the categories we gave it,
    # verbatim, or nothing. Never trust it to invent a new one.
    return category if category in categories else None


def _looks_like_category_label(text: str) -> bool:
    """True if text reads like a short category label, not prose or contact info."""
    text = text.strip()
    if not text or "\n" in text:
        return False
    if len(text) > 60:
        return False
    if text.endswith("."):
        return False
    return True


def find_skills_table(doc):
    """Return the first table that looks like a 2-column category/skills table.

    Heuristic, not a guarantee: exactly 2 columns, and every row's first-column
    cell reads like a short category label rather than a paragraph of prose or
    contact details. Returns None if no table matches — callers should treat
    that as "skip tailoring for this CV" rather than an error, since CVs whose
    skills section isn't laid out as a table aren't supported in v1.
    """
    for table in doc.tables:
        if len(table.columns) != 2:
            continue
        if all(_looks_like_category_label(row.cells[0].text) for row in table.rows):
            return table
    return None


def find_category_cell(table, category: str):
    """Return the skills cell for a category row, or None if no row matches.

    Matches on the row's first cell text (the category label) against the
    category string exactly, after stripping whitespace.
    """
    for row in table.rows:
        if row.cells[0].text.strip() == category:
            return row.cells[1]
    return None


def _append_text(existing: str, skill: str) -> str:
    return f"{existing}, {skill}" if existing else skill


def append_skill(cell, skill: str) -> None:
    """Append a skill to a category cell's existing comma-separated list.

    Edits the cell's first paragraph in place, preserving its formatting.
    Requires the cell to already have at least one run to borrow formatting
    from — true for every real category row, since a category only exists
    because it already lists skills. Raises ValueError (via apply_edit) if
    that paragraph has mixed formatting, or has no runs at all.
    """
    paragraph = cell.paragraphs[0]
    apply_edit(paragraph, _append_text(paragraph.text.strip(), skill))


def propose_edits(doc, gap_suggestions: list[dict]) -> list[dict]:
    """Propose CV edits for a job's buried gap suggestions, without applying them.

    Returns a list of {skills, category, current_text, proposed_text} dicts —
    one per category that has at least one buried suggestion mapped to it.
    Multiple skills landing in the same category are grouped into a single
    proposal (skills is a list of {skill, evidence}), rather than one proposal
    per skill: two independent proposals targeting the same cell would clobber
    each other when applied, since each would be computed from the same
    original text with no awareness of the other's edit.

    "missing" suggestions are never proposed (no real evidence to ground
    them), and a buried suggestion with no genuine category fit is silently
    skipped, same as pick_target_category's own honesty-line guard. Returns
    [] if this CV's skills table can't be found at all.
    """
    table = find_skills_table(doc)
    if table is None:
        return []

    categories = [row.cells[0].text.strip() for row in table.rows]
    buried = [g for g in gap_suggestions if g.get("status") == "buried"]

    gaps_by_category = {}
    for gap in buried:
        category = pick_target_category(categories, gap["skill"], gap["evidence"])
        if category is None:
            continue
        gaps_by_category.setdefault(category, []).append(gap)

    proposals = []
    for category, gaps in gaps_by_category.items():
        cell = find_category_cell(table, category)
        current_text = cell.paragraphs[0].text.strip()
        proposed_text = current_text
        for gap in gaps:
            proposed_text = _append_text(proposed_text, gap["skill"])
        proposals.append({
            "skills": [{"skill": g["skill"], "evidence": g["evidence"]} for g in gaps],
            "category": category,
            "current_text": current_text,
            "proposed_text": proposed_text,
        })
    return proposals


def apply_proposals(doc, proposals: list[dict]) -> None:
    """Apply user-confirmed proposals to doc.

    Each proposal's proposed_text may have been edited by the user in the
    review UI — this applies exactly that text, not a freshly recomputed
    append, so user edits are respected as-is.
    """
    table = find_skills_table(doc)
    for proposal in proposals:
        cell = find_category_cell(table, proposal["category"])
        apply_edit(cell.paragraphs[0], proposal["proposed_text"])


def _formatting_signature(run):
    color = run.font.color.rgb if run.font.color and run.font.color.type else None
    return (run.bold, run.italic, run.font.size, color)


def is_editable(paragraph) -> bool:
    """True if every run in the paragraph shares the same formatting."""
    if not paragraph.runs:
        return False
    signatures = {_formatting_signature(r) for r in paragraph.runs}
    return len(signatures) == 1


def apply_edit(paragraph, new_text: str) -> None:
    """Replace a paragraph's text in place, preserving its formatting.

    All new text goes into the first run; any remaining runs are blanked
    out. Safe only because is_editable() has already confirmed every run
    in the paragraph shares identical formatting.
    """
    if not is_editable(paragraph):
        raise ValueError("Paragraph has mixed formatting; cannot safely edit.")
    paragraph.runs[0].text = new_text
    for run in paragraph.runs[1:]:
        run.text = ""
