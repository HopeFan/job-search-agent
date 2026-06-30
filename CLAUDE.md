# Job Search Assistant — Project Context

## Who I am
I'm a data engineer learning AI engineering by building this project.
My PRIMARY goal is to UNDERSTAND what I build, not just to ship it.
A working app I can't explain is a failure. Treat me as a learner.

## How to work with me  (THIS IS THE MOST IMPORTANT SECTION)
- Go SLOW. Build ONE small, reviewable piece at a time.
- BEFORE writing code, explain in plain words: what you're about to build,
  why, and what alternatives exist. Concept first, code second.
- After each piece, STOP. Let me read it and confirm I understand before
  continuing. Do not proceed on your own.
- Do NOT build ahead. Do NOT scaffold multiple steps at once. One step.
- After each step, ask me to explain back what we just built in my own words.
  If I can't, we're not done — re-explain, don't move on.
- When you make a small implementation choice (naming, structure), flag it
  out loud. Don't bury decisions.
- If a DESIGN decision comes up that isn't already settled below, ASK me.
  Never assume or silently re-litigate a locked decision.
- Prefer simple, transparent code over clever or framework-heavy code.
  I should be able to read and understand every line.

## What this project is
A job-search assistant for TWO private users (me and my wife).
For each user it: fetches jobs, ranks them against that user's master CV,
helps tailor the CV and outreach per role, and tracks applications through
to interview. Eventually hosted so each of us logs in via a URL.

Users: `ehesami`, `jsamadi`. Each sees ONLY their own data by default.

## Locked decisions — do NOT re-litigate or violate
SOURCES
- SEEK via Apify (actor's plain HTTP API) is the FIRST source.
- LinkedIn via Apify is Phase 2 (later).
- Sources are PLUGGABLE ADAPTERS: every source maps to one common job shape.
- A source failing = a degraded day, never a crash (graceful degradation).
- Search is FETCH-WIDE-BY-TITLE, then RANK-NARROW-BY-CV. You cannot ask
  SEEK to "match my CV"; the matcher does the narrowing.

MATCHING
- Rate jobs on a RUBRIC (skills / seniority / location / must-haves).
- Output = RANKING + BANDS (strong/moderate/weak) + REASONS.
- NEVER output a percentage match score. (LLM percentages are false precision.)
- Include STRETCH roles, labelled with the gap. Don't hide them.
- FILTER-THEN-RATE: cheap embedding pre-filter, then deep-rate only the
  survivors. BUT build "rate every job" FIRST to learn it, add the filter after.
- Weak-band jobs stay VISIBLE/reviewable, never hidden.
- When a master CV is updated, RE-RANK stored jobs against the new version.

CV
- Master CV is a Word .docx = source of truth for formatting.
- Also keep a DERIVED STRUCTURED view (skills/roles) — that's what the AI uses.
- Gap suggestions must be GROUNDED in the real CV. HONESTY LINE: surface real
  buried experience, never invent keywords I can't back up in an interview.
- Tailored CVs preserve formatting (targeted content edits only), saved as
  versioned .docx (e.g. EhesamiJune26CV) + a generated PDF, linked to the app.

OUTREACH & GENERATION
- Email + LinkedIn messages are DRAFT-ONLY. I paste and send. NEVER auto-send.
- Post-interview thank-you drafts: same rule, grounded in that round's notes.
- Contact/email extracted ONLY when present in the posting. NEVER fabricated.

GROUNDING (applies everywhere)
- Ground every factual claim in a real source. If there's no source, say so.
  Never fabricate (salaries, contacts, company facts, CV content).

INTERFACE & USERS
- WEB APP is the primary interface (my wife won't use a terminal).
- Keep the UI CLEAN via a component library — NOT hand-crafted "beautiful".
  Real visual polish is deferred to a later optional pass.
- Simple, standard, library-based LOGIN. Light identity, not enterprise auth.
- Daily digest shown in the web app AND emailed to each user's own address.
- A CLI may exist as a dev/admin tool, but the web app is the user surface.

STACK (lightweight on purpose; don't add weight without hitting a real wall)
- Python. One LLM SDK called directly (no framework wrapping it).
- SQLite for everything (data, vectors, tracker) — NOT Postgres.
- Embeddings stored in SQLite — NOT a vector DB.
- Agent loops written as plain Python — NOT LangChain etc. I want to learn
  the loop, not import it.
- httpx for Apify calls. python-docx + a PDF lib for CVs.
- A simple web framework + component library. An email/SMTP service. .env for secrets.

## Boundaries — deliberately NOT in v1
No auto-apply. No auto-send. No fabricated data. No fine-tuning (prompting +
RAG only). No vector DB / Postgres. No heavy infra / monitoring stack / SLAs.
No public multi-tenant product (that's a much later "Game 1" phase).
No hand-polished UI.

## Observability (lightweight, build it in as we go)
Log per LLM call: token usage, cost, which prompt version, and outcome.
Log pipeline runs (jobs pulled, deduped, sources that failed). To file/SQLite.
No dashboards or tracing platforms in v1.

## Where the detailed plan lives
See PLAN.md for the ordered build steps and current progress.
Update PLAN.md as we finish each step. Record tradeoffs in its notes section —
that becomes my design doc later.

## Reminder to Claude Code
Your job here is to TEACH me to build this, not to build it for me.
Speed is not the goal; my understanding is. When in doubt, slow down and explain.
