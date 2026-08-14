# Decisions

Trade-offs captured as they were made, for interview prep while the reasoning is fresh.

**Gemini over other providers.** The brief allows any provider; Gemini's free tier and
native structured-output (`response_schema`) support made it the fastest path to
schema-validated triage/grounding/synthesis without hand-rolling JSON-mode prompting.
The `AIProvider` protocol in `app/ai/provider.py` keeps this swappable - only
`app/ai/gemini.py` imports the SDK.

**RRF over score normalization.** Vector cosine distance and `ts_rank_cd` live on
incomparable scales. Normalizing both to [0,1] and averaging requires picking a
normalization scheme (min-max over what population? per-query? global?) that's
arbitrary and breaks the moment score distributions shift. RRF only needs each
list's *rank*, which is directly comparable, so there's nothing to calibrate.

**GROUNDING_MIN_SCORE=0.020 with RRF_K=60 has a real consequence, verified while
building this**: a single-list top hit maxes out at `1/(60+1) ≈ 0.0164`, below the
0.020 threshold. That means grounding only ever answers (rather than abstains) when
*both* vector and lexical agree near the top - not just one signal. Confirmed this
against a live Postgres: without embeddings (no API key), literally every incident
abstains, even ones with a strong lexical match. That's arguably the right default -
"sufficient evidence" should mean cross-modal agreement - but it does mean the
abstain-without-a-key path isn't just the "no evidence" case, it's the *only*
reachable case. Documented in the limitations section rather than tuned away.

**Deterministic priority, not model-generated.** The impact/urgency → priority
matrix is a fixed Python dict. The model reads free text and estimates impact/urgency
(a genuinely fuzzy judgment call worth an LLM); priority itself is a policy lookup a
human already decided on paper. Keeping it in code means identical (impact, urgency)
always yields identical priority - reproducible and auditable, not a second dice roll.

**Human-in-the-loop publishing everywhere.** Triage never writes to the incident
(returns a proposal; `/apply-triage` is a separate call the UI only fires after
Accept). KB synthesis always lands as a `draft`; publishing is a separate, explicit
action. This is slower than auto-applying but it's the actual safety property the
brief is testing for - the model proposes, a human is accountable for what lands.

**Storm clustering and duplicate detection are pure math, not an LLM call.**
Cosine similarity over embeddings already computed at incident-creation time is one
index lookup. Asking a model "are these the same incident?" would be slower, cost
money per comparison, and - critically - could return different answers for the
same inputs on different days, breaking reproducibility. The one LLM call in
`services/correlation.py` is the storm's one-line summary, which is genuinely
generative, not a similarity judgment.

**Seed subset size and the synthetic storm.** `SEED_TICKET_LIMIT=300` balances a
populated-feeling queue against seed/embedding time. The free HuggingFace sample's
`outage_related` flag is always `False` in the 1000-row sample actually inspected,
and no natural same-category cluster exists within any 30-minute window (checked
against the real data, not assumed) - so `seed/load.py` adds 5 hand-written VPN-outage
incidents timestamped within a 20-minute window specifically so storm clustering has
something to find on first run. This is disclosed in the README, not hidden.

**Hybrid retrieval's lexical half uses OR-joined lexemes, not `websearch_to_tsquery`
directly.** Discovered while testing against a live DB: `websearch_to_tsquery` ANDs
every bare word together, which is correct for a short user search box but wrong when
the "query" is an entire incident title+description matched against short KB
articles - requiring every word to appear made real matches score zero. Fixed by
tokenizing the query text server-side (same `to_tsvector('english', ...)` used to
build `search_tsv`) and OR-joining the lexemes before ranking with `ts_rank_cd`.

**SSE over token-by-token model streaming.** Gemini's structured JSON output isn't
naturally streamable at the token level in a way a client can partially parse. The
`/ground` endpoint resolves the full grounded answer first (so `AI_UNAVAILABLE` /
`RATE_LIMITED` surface as normal JSON errors before any bytes are sent), then
streams the diagnosis text word-by-word over SSE so latency still reads as progress
rather than a blocking spinner.

**No Docker on the build machine.** Built and verified against a native Windows
PostgreSQL 18 install (with a third-party-compiled `pgvector` extension, since
pgvector doesn't publish official Windows binaries) instead of the `pgvector/pgvector`
Docker image. `docker-compose.yml` still targets that official image for anyone
running this on a machine with Docker - the local setup was purely to get real
end-to-end verification during development. See the README's "running without Docker"
notes for exactly what was reproduced this way.

**No GEMINI_API_KEY for most of this build, then a real one partway through.**
Every AI-independent path (auth, CRUD, validation, optimistic concurrency, the
abstain guardrail itself, hybrid retrieval, KB browsing, error envelopes) was
exercised end-to-end against a live Postgres and a live browser before any key
existed. A real key was added later and used to verify every AI-dependent path live:
real triage output, a real grounded answer citing a genuine past incident, a real
AI-drafted KB article from a resolution note, publishing it, a *new* incident
worded differently getting answered by citing that same article minutes later, and
real storm clustering with an AI-written summary. That's the full demo script,
confirmed working end to end, not just implemented.

**The key turned out to be capacity-constrained, and that shaped two changes.**
`gemini-3.5-flash` (current per docs at build time) returned a persistent `503`
"experiencing high demand" for structured-output calls; `gemini-flash-latest`
worked - default model switched (see `.env.example`). Separately, a handful of
single calls needed 2-3 retries to succeed even with backoff, and running the eval
harness's 25 back-to-back triage calls with no pacing burned through the key's
per-minute quota (24/25 came back `RATE_LIMITED`, which is the app correctly
protecting itself, not an accuracy problem) - fixed by adding a 4s pace between eval
calls. Both are now baked into the code (`app/ai/gemini.py`'s retry now covers 503s,
not just 429s; `eval/run_eval.py` paces triage calls), not just noted as caveats.
