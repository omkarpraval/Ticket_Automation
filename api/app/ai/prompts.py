"""All prompt templates, versioned. Routers and services never build prompts inline —
they call the *_prompt() functions here so the exact wording used for any historical
ai_runs row can be reconstructed from prompt_version alone.
"""

PROMPT_VERSION = "v1"

TRIAGE_SCHEMA = {
    "type": "object",
    "properties": {
        "category": {"type": "string"},
        "affected_system": {"type": "string"},
        "impact": {"type": "integer", "minimum": 1, "maximum": 4},
        "urgency": {"type": "integer", "minimum": 1, "maximum": 4},
        "suggested_team": {"type": "string"},
        "entities": {
            "type": "object",
            "properties": {
                "error_codes": {"type": "array", "items": {"type": "string"}},
                "applications": {"type": "array", "items": {"type": "string"}},
                "platforms": {"type": "array", "items": {"type": "string"}},
            },
            "required": ["error_codes", "applications", "platforms"],
        },
        "summary": {"type": "string"},
        "rationale": {
            "type": "object",
            "properties": {
                "category": {"type": "string"},
                "impact": {"type": "string"},
                "urgency": {"type": "string"},
                "team": {"type": "string"},
            },
            "required": ["category", "impact", "urgency", "team"],
        },
    },
    "required": ["category", "affected_system", "impact", "urgency", "suggested_team", "entities", "summary", "rationale"],
}

GROUNDING_SCHEMA = {
    "type": "object",
    "properties": {
        "has_sufficient_evidence": {"type": "boolean"},
        "diagnosis": {"type": "string"},
        "recommended_steps": {"type": "array", "items": {"type": "string"}},
        "citations": {"type": "array", "items": {"type": "string"}},
        "confidence_reason": {"type": "string"},
        "escalate_to": {"type": "string", "nullable": True},
    },
    "required": ["has_sufficient_evidence", "diagnosis", "recommended_steps", "citations", "confidence_reason"],
}

SYNTHESIS_SCHEMA = {
    "type": "object",
    "properties": {
        "action": {"type": "string", "enum": ["create", "update", "skip"]},
        "target_article_reference": {"type": "string", "nullable": True},
        "title": {"type": "string"},
        "symptom": {"type": "string"},
        "cause": {"type": "string"},
        "resolution_steps": {"type": "array", "items": {"type": "string"}},
        "verification": {"type": "string"},
        "tags": {"type": "array", "items": {"type": "string"}},
        "reasoning": {"type": "string"},
    },
    "required": ["action", "title", "symptom", "cause", "resolution_steps", "verification", "tags", "reasoning"],
}


def triage_prompt(*, title: str, description: str, categories: list[str], teams: list[str]) -> str:
    return f"""You are the triage assistant for an IT service desk. Read the incident below and
propose a classification. You do NOT decide priority - that is computed deterministically
from the impact and urgency you report, so focus on accurate reading of the ticket.

Known categories (pick exactly one, verbatim): {", ".join(categories)}
Known teams (suggested_team must be exactly one of these, verbatim): {", ".join(teams)}

Incident title: {title}
Incident description:
{description}

Rate impact and urgency on a 1-4 scale where 1 is most severe:
impact: 1=organization-wide outage, 2=department/team-wide, 3=single user blocked, 4=single user inconvenienced.
urgency: 1=needs action within minutes, 2=within hours, 3=within a day, 4=no real time pressure.

Extract entities literally mentioned in the text (error codes, application names, platforms).
Write a one-sentence summary (max 200 chars) and a short rationale for each of your
category, impact, urgency and team choices, referencing specific words from the ticket.
Respond with JSON matching the provided schema only."""


def grounding_prompt(*, incident_title: str, incident_description: str, context_block: str) -> str:
    return f"""You are answering an IT support incident using ONLY the context block below,
which contains knowledge base articles and past resolved incidents. Do not use any
outside knowledge, and do not guess. If the context does not contain enough information
to safely resolve this incident, set has_sufficient_evidence to false, leave diagnosis
and recommended_steps minimal, and set escalate_to to the team that should take it.

Every string in "citations" MUST be a reference token (like "KB-014" or "INC-0388") that
appears literally in the context block below. Never invent a citation.

Context:
{context_block}

Incident title: {incident_title}
Incident description:
{incident_description}

Respond with JSON matching the provided schema only."""


def synthesis_prompt(
    *, incident_title: str, incident_description: str, resolution_note: str, comments_block: str, related_block: str
) -> str:
    return f"""You are drafting a knowledge base article from a just-resolved IT incident, so the
next person with the same problem can self-serve. If this was a one-off issue with no
reusable lesson (e.g. a fix specific to one user's broken hardware, or a duplicate of
existing knowledge), set action to "skip" and explain why in reasoning - do not force
an article into existence.

If an existing article below already covers this exact problem, set action to "update"
and target_article_reference to its reference; otherwise action "create".

Incident title: {incident_title}
Incident description:
{incident_description}

Comment thread:
{comments_block}

Resolution note (written by the resolving agent):
{resolution_note}

Existing related articles (for dedup / update decisions):
{related_block}

Respond with JSON matching the provided schema only. resolution_steps must be an
ordered list of concrete, actionable steps."""


def storm_summary_prompt(*, incident_titles: list[str], shared_category: str | None) -> str:
    titles = "\n".join(f"- {t}" for t in incident_titles)
    category_hint = f" They share the category '{shared_category}'." if shared_category else ""
    return f"""The following {len(incident_titles)} incidents arrived within a short window and were
automatically clustered as likely instances of the same underlying problem.{category_hint}

{titles}

Write a concise problem title (max 80 chars) on the first line, then a 2-3 sentence
summary of the likely shared root cause on the following lines. Do not use markdown."""
