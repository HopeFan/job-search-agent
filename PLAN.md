# Build Plan & Progress

> Update this file as we go. Tick steps off, and record decisions/tradeoffs
> in the log at the bottom — that log becomes the design doc later.

## Current step: 10

## Working ritual (every step)
1. Claude explains the concept + why, before any code.
2. Build ONE small piece.
3. I review it and confirm I understand.
4. I explain it back in my own words. If I can't → not done yet.
5. Tick the step, note any decision, move on.

---

## Phase 1 — the engine + cockpit  (me, then my wife)

Build locally through step 10. Deploy around step 11. Then ship to the host.

| # | Step | Technique(s) I'm learning here | Local/Hosted | Done? |
|---|------|--------------------------------|--------------|-------|
| 1 | Project skeleton + DB spine (users, jobs, ownership) | Data modeling for AI; per-user foundation | Local | [x] |
| 2 | Web app skeleton + simple login (each user → own view) | Light auth; activating the per-user model | Local | [x] |
| 3 | Saved searches per user (editable title+location lists) | Config/state modeling; fetch-wide concept | Local | [x] |
| 4 | SEEK adapter (Apify HTTP) → normalize → store | Tool/API integration; pluggable adapters | Local | [x] |
| 5 | Dedup + lifecycle (never-delete, mark stale) | Idempotency; data lifecycle | Local | [x] |
| 6 | CV upload + structured extraction (.docx → skills/roles) | Structured output; document parsing | Local | [x] |
| 7 | Job extraction (description → structured fields) | Structured output; entity extraction | Local | [x] |
| 8 | Matcher v1 — LLM rubric, RATE EVERY JOB | Probabilistic thinking; rubric scoring; prompt design | Local | [x] |
| 9 | Filter-then-rate (embeddings pre-filter) | Embeddings; semantic search; RAG; cost-aware design | Local | [x] |
| 10 | Observability (tokens, cost, prompt version, outcomes) | The AI harness; lineage | Local | [x] |
| 11 | **FIRST DEPLOY** — host it, login + URLs working for both of us | Deployment; secrets in prod; the "to production" muscle | → Hosted | [ ] |
| 12 | CV gap suggestions (grounded, honesty line) | Grounding / anti-hallucination | Hosted | [ ] |
| 13 | CV tailoring — versioned .docx + PDF | Document processing; formatting preservation | Hosted | [ ] |
| 14 | Draft email + LinkedIn message (draft-only) | Generation; tone control; guardrails | Hosted | [ ] |
| 15 | Tracker (applied/emailed/messaged, dates, notes, CV version, search, download) | Data modeling; knowing where AI doesn't belong | Hosted | [ ] |
| 16 | Interview tracking (multi-round) + thank-you drafts | Lifecycle modeling; grounded generation | Hosted | [ ] |
| 17 | Insights / analytics (top skills, salary trends) | Aggregation; embeddings-as-data | Hosted | [ ] |
| 18 | Interview-prep agent (company research from web + JD) | Agent loops; tool calling; multi-source synthesis; RAG | Hosted | [ ] |
| 19 | Daily run + email digest per user | Orchestration; scheduling; idempotency | Hosted | [ ] |
| 20 | Evals (hand-label ~30 jobs, score the matcher) | Evals — the probabilistic replacement for unit tests | Local/Hosted | [ ] |
| 21 | Design doc (decisions + tradeoffs, from the log below) | Tradeoff reasoning — the interview differentiator | — | [ ] |

## Phase 2 — later (after the SEEK pipeline is solid)
| # | Step | Technique | Done? |
|---|------|-----------|-------|
| P2-1 | LinkedIn adapter (second source via Apify) | Proving the pluggable design | [ ] |
| P2-2 | MCP upgrade of the Apify call | MCP — by upgrading something I already understand | [ ] |

## "Game 1" — much later, only if opening to strangers
Public multi-tenant: real auth, privacy compliance, billing, scaling, robustness
across unknown users. NOT now. Listed only so it's not confused with Phase 1.

---

## Sequencing principles (why the order is what it is)
- Never build a thing before the thing it depends on exists.
- Never optimize before the simple version works (rate-all before filter-then-rate).
- Build the engine locally first; deploy once there's something worth hosting.
- The hard AI learning is steps 6–9 and 18. Slow down there. That's the point.
- The unglamorous steps (20, 21) are the interview differentiators. Don't skip them.

## Estimated running cost (two private users)
~$10–20/month typical, near-$0 on free tiers. App host $5–10, domain ~$1,
LLM <$1–5 (filter-then-rate keeps it tiny), Apify ~$1, email free tier, DB = SQLite ($0).
Verify live hosting prices at step 11.

## Decisions & tradeoffs log  (→ becomes the design doc)
- Ranking + bands over percentage: LLM percentages are false precision; bands
  survive the model's noise and the reasons are more useful than a number.
- SEEK first via Apify (not Adzuna backbone): Adzuna doesn't cover SEEK (rivals),
  and SEEK coverage matters for the AU market. Accepting scraper flakiness as a
  known tradeoff; pluggable design means a reliable source can be added later.
- Filter-then-rate: biggest cost lever ($0.50 vs $5/mo) and core retrieval pattern.
- SQLite not Postgres / no vector DB: unjustified complexity at two-user scale.
- Web + simple login (not CLI): real second user who won't use a terminal.
- Clean-not-beautiful UI: polish is low-value for an AI-eng goal; defer it.
- Observability via SQLite tables (llm_calls, pipeline_runs): keeps it consistent
  with the rest of the stack; queryable without log-grepping. tracked_call() wrapper
  centralises token counting and cost calculation in one place rather than repeating
  it in each LLM module. save_job() now returns rowcount so new vs duplicate counts
  are tracked without duplicating SQL.

## jsamadi display name: "J. Samadi"  (placeholder — confirm real name)
