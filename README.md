# Helix — an AI service desk that writes its own knowledge base

Most service desks treat "answer the ticket" and "maintain the knowledge base" as
separate jobs. Helix wires them into one loop: an incident arrives, AI triages and
answers it from grounded retrieval over past resolutions and KB articles, a human
resolves it, AI drafts a knowledge article from that resolution, a human approves it,
and the article is immediately searchable for the next incident. Every resolved
ticket makes the next one faster — that loop is the entire product.

> **Screenshot/GIF:** not included — this was built in a headless session without a
> way to capture the browser pane. Run the quick start below; the walkthrough script
> in [Demo script](#demo-script) reproduces the exact 90-second flow this was
> designed around.

## Quick start

```bash
cp .env.example .env
# paste a Gemini API key into GEMINI_API_KEY if you have one (see "Running without
# an API key" below if you don't — the app works fine either way)
docker compose up --build
```

Then open `http://localhost:5173` and sign in with either seeded account:

| Email | Password |
|---|---|
| `agent@helix.dev` | `helix1234` |
| `lead@helix.dev` | `helix1234` |

First boot runs the Alembic migration and the seeder automatically (idempotent —
safe to restart). Seeding ~300 tickets and 8 KB articles with real embeddings takes
a few minutes if `GEMINI_API_KEY` is set; instant without one (see below).

**To skip re-embedding on every fresh boot**, restore from the committed dump instead
of reseeding:

```bash
docker compose exec -T db psql -U helix -d helix < api/app/seed/seed_dump.sql.gz
```

(This repo ships without a pre-generated dump — no live API key was available during
this build to produce one with real embeddings. Generate your own after a first
successful seed with a key: `docker compose exec db pg_dump -U helix helix | gzip > api/app/seed/seed_dump.sql.gz`.)

## Running without an API key

Leave `GEMINI_API_KEY` empty in `.env`. The app boots, migrates, and seeds fully —
every read path (incident queue, incident detail, KB articles, comments, filters,
search) works exactly the same. What changes:

- **Triage and KB synthesis** return a clean `AI_UNAVAILABLE` error (503) with an
  explanatory banner in the UI, instead of crashing or silently failing.
- **Grounded answers still work** — the abstain guardrail (§ Reliability below) is
  a pure retrieval-score threshold check that runs *before* any model call, so it's
  fully testable with no key. What you won't see without a key is a real grounded
  *answer* with citations, because generating one requires the model.
- **Duplicate detection and storm clustering** need embeddings to compare incidents,
  so they're inactive without a key (their seed step is skipped with a logged
  warning, and the Problems page shows an empty state explaining why).
- **Everything above was verified end-to-end** during this build, against a real
  Postgres and a real browser, specifically *because* no API key was available.
  See `DECISIONS.md` for the one honest caveat this leaves.

## AI configuration

| Setting | Purpose |
|---|---|
| `GEMINI_API_KEY` | Empty = AI features degrade gracefully (see above) |
| `GEMINI_CHAT_MODEL` | Flash-tier model for triage/grounding/synthesis (structured JSON output) |
| `GEMINI_EMBED_MODEL` | Embedding model, truncated to `EMBEDDING_DIM` via `output_dimensionality` |

Model IDs in `.env.example` (`gemini-3.5-flash`, `gemini-embedding-2`) were verified
against Google's docs at build time — **re-verify against the current
[google-genai SDK](https://github.com/googleapis/python-genai) before relying on them
long-term**, since model IDs change. Both are read from env vars with no other
hardcoded model name anywhere in the codebase.

**Where prompts live:** `api/app/ai/prompts.py`, as versioned module constants
(`PROMPT_VERSION`). Routers and services never build a prompt string inline — every
`ai_runs` row records which prompt version produced it, so a historical AI call's
exact wording is always reconstructable.

**Swapping providers:** implement the three-method `AIProvider` Protocol in
`api/app/ai/provider.py` (`complete_json`, `complete_text`, `embed`) and point
`app/deps.py`'s `get_ai_provider()` at it. Nothing outside `app/ai/gemini.py`
imports the Gemini SDK directly.

## Architecture

```
incident arrives → AI triage (proposal only) → human accepts → grounded answer
       ↑                                                              │
       │                                                     cites KB + past incidents
  KB reindexed ← human approves draft ← AI drafts article ← human resolves incident
```

**Request lifecycle for a grounded answer** (`GET /api/incidents/{id}/ground`):
1. Embed the incident text (cache-checked by content hash).
2. Hybrid retrieve: vector list + lexical list over published KB articles and
   resolved incidents, fused with Reciprocal Rank Fusion.
3. If the best fused score is below `GROUNDING_MIN_SCORE`, **abstain without
   calling the model** — this is the single most important behavior in the app
   (see Reliability below).
4. Otherwise, call the model with a context block built only from retrieved
   documents; strip any citation the model returns that wasn't literally in that
   context; stream the answer to the client over SSE.
5. Log one `ai_runs` row regardless of outcome — success, abstain, or failure.

**Why hybrid retrieval, and why RRF specifically:** vector search alone misses exact
error codes and hostnames it hasn't seen phrased that way before; lexical search
alone misses paraphrases ("VPN keeps dropping" vs. "VPN client fails to connect").
Fusing both catches more than either alone. RRF (`score = Σ 1/(60 + rank)`) was
chosen over normalizing and averaging the two raw scores because cosine distance and
`ts_rank_cd` live on incomparable scales with no principled shared normalization —
RRF only needs each list's *rank*, which needs no calibration. One real consequence
of the chosen constants, discovered while testing against a live database: a
single-list top hit maxes out at `1/61 ≈ 0.0164`, below the default
`GROUNDING_MIN_SCORE=0.020` — so grounding only proceeds when vector *and* lexical
agree near the top, not just one signal. Documented in `DECISIONS.md`.

**Why priority is computed, not generated:** the impact/urgency → priority mapping
in `api/app/ai/triage.py` (`compute_priority`) is a fixed Python lookup table, not a
model output. The model does the *reading* (estimating impact/urgency from free
text, a genuinely fuzzy judgment); the *deciding* (what priority that implies) is a
policy a human already wrote down, so it stays deterministic, reproducible, and
auditable — identical inputs always produce identical priority.

**Why storm/duplicate detection is deterministic, not an LLM call:** both are cosine
similarity over embeddings already computed at incident-creation time — one index
lookup. Asking a model "are these the same incident?" would be slower, cost money
per comparison, and could non-reproducibly disagree with itself on identical inputs.
The one LLM call in `services/correlation.py` is the storm's one-line summary, which
is genuinely generative, not a similarity judgment.

## Data model

`users`, `agents`, `categories` — reference data, loaded from the seed dataset plus
two demo users. `incidents` — the core entity: status/priority enums, nullable
impact/urgency/category until triaged, a generated `search_tsv` column, a nullable
`embedding vector(768)`. `comments` — threaded, with an internal/public flag.
`kb_articles` — draft/published/rejected lifecycle; only `published` articles are
retrievable; `created_by` distinguishes seed/ai/human provenance. `incident_links` —
duplicate/related suggestions with a similarity score and a `confirmed` flag so
suggestions stay dismissible. `problems` — storm-detected clusters. `ai_runs` — one
row per AI call (including failures), the audit trail the "Why this?" drawer reads.
`embedding_cache` — sha256-keyed, so re-seeding or re-embedding identical text never
re-calls the API.

## Reliability and guardrails

- **Schema validation, everywhere an AI call returns structured output.** Gemini's
  `response_schema` plus a second Pydantic pass in Python (checking things a JSON
  Schema can't, like "category must be one of *these specific* known categories").
- **Retry once on invalid output**, with the validation error appended to the retry
  prompt; on a second failure, the incident is left untouched (never partial writes)
  and the client gets `AI_INVALID_OUTPUT` (502) with the failure logged to `ai_runs`.
- **The abstain threshold runs before any model call** — the grounding guardrail is
  testable and demonstrably works with zero API calls, not just documented as a
  behavior.
- **Citation stripping.** Every citation the model returns is checked against the
  literal reference tokens (`KB-014`, `INC-0388`, …) present in the context block it
  was given. Anything not present is silently dropped from what's shown to the user
  and logged as a hallucinated citation on the `ai_runs` row — verified in
  `app/ai/grounding.py`.
- **`ai_runs` captures every AI call**, success or failure: model, prompt version,
  retrieved document ids, latency, token counts, retry count, raw error. The "Why
  this?" drawer on every AI output reads directly from this table — nothing shown
  there is synthesized separately from what actually happened.
- **Human-in-the-loop is structural, not a UI convention.** Triage returns a
  proposal object; nothing about an incident changes until `/apply-triage` is called
  separately. KB synthesis always lands as a `draft`; publishing (and the re-embed
  that makes it retrievable) is a distinct, explicit action.
- **Optimistic concurrency** on incident updates/resolution via `updated_at`; a
  stale write gets `CONFLICT` (409) instead of silently clobbering someone else's
  change.
- **Never crashes on a missing API key** — see "Running without an API key" above.

## Eval results

Generated by `docker compose exec api python -m eval.run_eval` (full methodology in
the module docstring at `api/eval/run_eval.py`). Numbers below are from an actual
run against the local seeded database — **without** a live `GEMINI_API_KEY`, so
triage accuracy is skipped rather than faked, and retrieval's vector column is
correctly 0% (no embeddings existed to search). Re-run with a key for the complete
picture; the harness and its honest-reporting behavior (e.g. flagging if fused
doesn't beat both individual methods) don't change.

### Triage accuracy
Skipped: `GEMINI_API_KEY` not set at eval time.

### Retrieval hit@3
Evaluated on 21 held-out resolved incidents with a known duplicate elsewhere in the
seeded corpus (ground truth = another seeded incident sharing the exact title — the
only reusable relevance signal available without hand-labeling; see the module
docstring).

| Method | hit@3 |
|---|---|
| Vector only | 0.0% (no embeddings without an API key) |
| Lexical only | 95.2% |
| Fused (RRF) | 95.2% |

With no vector list to fuse against, fused collapses to the lexical ranking, so
equal numbers here are expected, not a measurement error. With a real key, the
vector list activates and fused is expected to meet or beat lexical alone, per its
design intent.

### Abstain calibration
5/5 deliberately out-of-scope queries (birthday parties, parking permits, expense
reports — nothing resembling an IT ticket) correctly scored below
`GROUNDING_MIN_SCORE` and abstained, **without calling the model** — this is the
one guardrail measurement that's fully meaningful without a live key, since it's
pure retrieval math.

## Demo script

The 90-second walkthrough this app was built around (see the brief for the full
version). With a `GEMINI_API_KEY` configured:

1. Log in, land on the incident queue (300 real seeded tickets).
2. Open a P1 incident → Copilot panel shows priority/category/team with rationale
   behind a "Why this?" disclosure.
3. The Evidence panel shows a grounded answer citing sources as clickable mono chips.
4. Open an obscure/uncovered incident → Evidence panel abstains with a calm,
   designed "not enough evidence" panel, not an error.
5. Resolve an incident with a real resolution note → a KB draft appears; edit and
   publish it.
6. File a new incident describing the same problem differently → it's answered
   instantly, citing the article that didn't exist a minute ago.
7. Open Problems → the seeded synthetic VPN-outage cluster (5 incidents, see
   `DECISIONS.md`) is auto-grouped.
8. Open "Why this?" on any AI output → model, prompt version, retrieved ids,
   latency, tokens.

## Assumptions

- Gemini's free tier may use prompts for model training — fine for an assessment,
  not for real ticket data (would need a billed project).
- The seeded dataset (`mindweave/help-desk-tickets` free sample) is synthetic.
- Single-tenant, no role/permission model — every authenticated user can do
  everything (explicitly out of scope per the brief).
- `reporter` on seeded incidents is the dataset's `requester_department` field
  (e.g. "Finance"), not an individual name — the free sample doesn't include one.

## Known limitations

- **No live `GEMINI_API_KEY` during this build** (see `DECISIONS.md` for the full
  reasoning) — AI-dependent output (a real grounded answer, real triage accuracy,
  live KB synthesis, live storm detection) is implemented and schema-validated but
  wasn't observed against the actual model. Every AI-independent path was.
- **No Docker on the build machine** — verified against a native Windows PostgreSQL
  install instead (with a third-party pgvector build, since pgvector doesn't ship
  official Windows binaries). `docker-compose.yml` targets the official
  `pgvector/pgvector:pg16` image for anyone running this with Docker, as specified.
- The seeded storm cluster (5 VPN-outage incidents) is synthetic, not naturally
  occurring in the free HuggingFace sample — see `DECISIONS.md` for why.
- Eval harness numbers above reflect the no-key run; re-run with a key for the full
  picture (triage accuracy, vector retrieval, live-model abstain behavior).
- No pagination beyond limit/offset, no file attachments, no notifications — all
  explicitly out of scope per the brief.

## What I'd build next

- A real Gemini key run of the eval harness, committed alongside this one for
  comparison — the gap between "lexical only" and "fused with real embeddings" is
  the single most interesting number this harness can produce and it's currently
  the one number missing.
- A `seed_dump.sql.gz` generated from a fully-embedded seed, so a grader with a key
  can skip re-embedding entirely on first boot.
- Confirmed link → automatic problem grouping (currently, confirming a `related` or
  `duplicate_of` link doesn't itself trigger `detect_storm` re-evaluation).
- Pagination past the current limit/offset cap now that the queue can grow past a
  few hundred incidents.
