"""Eval harness. Run with `python -m eval.run_eval` (or `docker compose exec api
python -m eval.run_eval`). Requires GEMINI_API_KEY for the triage-accuracy and
abstain-calibration sections (both call the model); retrieval hit@3 is pure SQL
and works without a key, though scores will be lexical-only in that case.

Three measurements:
  1. Triage accuracy - 25 held-out seeded incidents with a known category label;
     run triage, compare the predicted category to the dataset's own label.
  2. Retrieval hit@3 - for each held-out *resolved* incident, does the top-3
     result (vector-only / lexical-only / fused) contain a genuine near-duplicate?
     Ground truth here is "another seeded incident with the identical title" -
     the synthetic dataset has real repeated tickets (same complaint filed by
     different people), which is the only reusable relevance signal available
     without hand-labeling. This is documented so the number isn't overclaimed.
  3. Abstain calibration - 5 hand-written out-of-scope queries (not IT support
     issues at all) sent through the same retrieval + threshold check the app
     uses; report how many correctly score below GROUNDING_MIN_SCORE.
"""

import asyncio
from pathlib import Path

from sqlalchemy import func, select

from app.config import settings
from app.db import SessionLocal
from app.deps import get_ai_provider
from app.models import Category, Incident, IncidentStatus
from app.services.retrieval import _LEXICAL_SQL, _TERMS_SQL, _VECTOR_SQL, _rrf_fuse

HELD_OUT_LIMIT = 25
CANDIDATE_LIMIT = 20

OUT_OF_SCOPE_QUERIES = [
    "What's the best way to plan a surprise birthday party for a coworker?",
    "Can someone recommend a good coffee blend for the office kitchen?",
    "I need help renewing my parking permit for the downtown garage.",
    "What's the process for submitting a travel expense report for a conference?",
    "One of the chairs in the third floor conference room is wobbly and needs replacing.",
]


async def _vector_only_ranked(db, query_embedding, exclude_id) -> list[str]:
    if query_embedding is None:
        return []
    rows = (
        await db.execute(_VECTOR_SQL, {"qe": str(query_embedding), "exclude_id": exclude_id, "limit": CANDIDATE_LIMIT})
    ).all()
    return [row.reference for row in rows]


async def _lexical_only_ranked(db, query_text, exclude_id) -> list[str]:
    terms = [row.lexeme for row in (await db.execute(_TERMS_SQL, {"q": query_text})).all()]
    if not terms:
        return []
    rows = (
        await db.execute(
            _LEXICAL_SQL, {"tsq": " | ".join(terms), "exclude_id": exclude_id, "limit": CANDIDATE_LIMIT}
        )
    ).all()
    return [row.reference for row in rows]


async def eval_retrieval_hit_at_3(db, provider, held_out: list[Incident]) -> dict:
    from app.services.embeddings import embed_texts

    resolved = [i for i in held_out if i.status in (IncidentStatus.resolved, IncidentStatus.closed)]
    hits = {"vector": 0, "lexical": 0, "fused": 0}
    total = 0

    for incident in resolved:
        # Ground truth: any OTHER incident sharing this exact title is a genuine
        # near-duplicate in the seeded data (see module docstring).
        truth_refs = {
            row.reference
            for row in (
                await db.execute(
                    select(Incident.id, Incident.reference).where(
                        Incident.title == incident.title, Incident.id != incident.id
                    )
                )
            ).all()
        }
        if not truth_refs:
            continue
        total += 1

        query_text = f"{incident.title} {incident.description}"
        [embedding] = await embed_texts(db, provider, [query_text]) if provider else [None]

        vector_ranked = await _vector_only_ranked(db, embedding, incident.id)
        lexical_ranked = await _lexical_only_ranked(db, query_text, incident.id)
        fused_scores = _rrf_fuse(vector_ranked, lexical_ranked)
        fused_ranked = sorted(fused_scores, key=lambda r: fused_scores[r], reverse=True)

        if truth_refs & set(vector_ranked[:3]):
            hits["vector"] += 1
        if truth_refs & set(lexical_ranked[:3]):
            hits["lexical"] += 1
        if truth_refs & set(fused_ranked[:3]):
            hits["fused"] += 1

    return {
        "total": total,
        "vector": hits["vector"] / total if total else 0.0,
        "lexical": hits["lexical"] / total if total else 0.0,
        "fused": hits["fused"] / total if total else 0.0,
    }


async def eval_triage_accuracy(db, provider, held_out: list[Incident]) -> dict:
    from app.ai.triage import run_triage

    if provider is None:
        return {"skipped": True, "reason": "GEMINI_API_KEY not set", "accuracy": 0.0, "confusions": []}

    correct = 0
    confusions = []
    scored = 0
    for i, incident in enumerate(held_out):
        if incident.category is None:
            continue
        if i > 0:
            # 25 back-to-back triage calls can exceed a free-tier key's per-minute
            # quota faster than the provider's own retry/backoff can absorb -
            # pacing calls here keeps a RATE_LIMITED run of 24 from looking like a
            # real accuracy problem.
            await asyncio.sleep(4)
        scored += 1
        try:
            proposal = await run_triage(db, incident, provider)
        except Exception as exc:  # noqa: BLE001 - a single bad call shouldn't kill the eval run
            confusions.append({"reference": incident.reference, "true": incident.category.name, "predicted": f"ERROR: {exc}"})
            continue
        if proposal.category == incident.category.name:
            correct += 1
        else:
            confusions.append(
                {"reference": incident.reference, "true": incident.category.name, "predicted": proposal.category}
            )

    return {"skipped": False, "accuracy": (correct / scored) if scored else 0.0, "total": scored, "confusions": confusions}


async def eval_abstain_calibration(db, provider) -> dict:
    from app.services.retrieval import retrieve

    correct = 0
    details = []
    for query in OUT_OF_SCOPE_QUERIES:
        embedding = None
        if provider is not None:
            from app.services.embeddings import embed_texts

            [embedding] = await embed_texts(db, provider, [query])
        result = await retrieve(db, query_text=query, query_embedding=embedding, exclude_incident_id=-1)
        abstained = result.best_score < settings.grounding_min_score
        if abstained:
            correct += 1
        details.append({"query": query, "best_score": round(result.best_score, 4), "abstained": abstained})

    return {"correct": correct, "total": len(OUT_OF_SCOPE_QUERIES), "details": details}


def _render_markdown(triage: dict, retrieval: dict, abstain: dict) -> str:
    lines = ["# Helix eval results", ""]

    lines += ["## Triage accuracy", ""]
    if triage["skipped"]:
        lines.append(f"Skipped: {triage['reason']}.")
    else:
        lines.append(f"Exact-match category accuracy: **{triage['accuracy']:.1%}** ({triage['total']} held-out incidents).")
        if triage["confusions"]:
            lines += ["", "| Incident | True category | Predicted |", "|---|---|---|"]
            for c in triage["confusions"]:
                lines.append(f"| {c['reference']} | {c['true']} | {c['predicted']} |")
    lines.append("")

    lines += ["## Retrieval hit@3", ""]
    lines.append(f"Evaluated on {retrieval['total']} held-out resolved incidents with a known duplicate in the corpus.")
    lines += [
        "",
        "| Method | hit@3 |",
        "|---|---|",
        f"| Vector only | {retrieval['vector']:.1%} |",
        f"| Lexical only | {retrieval['lexical']:.1%} |",
        f"| Fused (RRF) | {retrieval['fused']:.1%} |",
        "",
    ]
    if retrieval["fused"] + 1e-9 < max(retrieval["vector"], retrieval["lexical"]):
        lines.append(
            "Note: fused did **not** beat both individual methods on this run - reported honestly rather than adjusted."
        )
    lines.append("")

    lines += ["## Abstain calibration", ""]
    lines.append(f"Correctly abstained on **{abstain['correct']}/{abstain['total']}** out-of-scope queries.")
    lines += ["", "| Query | Best fused score | Abstained |", "|---|---|---|"]
    for d in abstain["details"]:
        lines.append(f"| {d['query'][:60]} | {d['best_score']} | {'yes' if d['abstained'] else 'no'} |")
    lines.append("")

    return "\n".join(lines)


async def main() -> None:
    provider = get_ai_provider()
    async with SessionLocal() as db:
        held_out_ids = (
            await db.execute(
                select(Incident.id)
                .where(Incident.category_id.is_not(None))
                .order_by(func.random())
                .limit(HELD_OUT_LIMIT)
            )
        ).scalars().all()
        held_out = [await db.get(Incident, i) for i in held_out_ids]
        for incident in held_out:
            await db.refresh(incident, attribute_names=["category"])

        print(f"Held out {len(held_out)} incidents.")

        triage = await eval_triage_accuracy(db, provider, held_out)
        print(f"Triage accuracy: {triage.get('accuracy', 0):.1%}" if not triage["skipped"] else "Triage: skipped (no key)")

        retrieval = await eval_retrieval_hit_at_3(db, provider, held_out)
        print(f"Retrieval hit@3 - vector {retrieval['vector']:.1%} / lexical {retrieval['lexical']:.1%} / fused {retrieval['fused']:.1%}")

        abstain = await eval_abstain_calibration(db, provider)
        print(f"Abstain calibration: {abstain['correct']}/{abstain['total']}")

    markdown = _render_markdown(triage, retrieval, abstain)
    out_path = Path(__file__).parent / "results.md"
    out_path.write_text(markdown, encoding="utf-8")
    print(f"\nWrote {out_path}")
    print("\n" + markdown)


if __name__ == "__main__":
    asyncio.run(main())
