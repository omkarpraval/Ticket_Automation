"""Idempotent seeder. Run with `python -m app.seed.load`.

Loads a subset of the mindweave/help-desk-tickets HuggingFace sample (tickets,
comments, categories, agents), the 8 handwritten KB articles, two demo users, and
a synthetic 5-incident VPN outage cluster so storm clustering has something to find
out of the box (the free sample's `outage_related` flag is always False and no
natural same-category cluster exists within any 30-minute window in 1000 rows -
this was checked against the actual data, not assumed).

Every seed_* function checks for existing rows before inserting, so re-running this
module never duplicates data.
"""

import asyncio
import csv
import logging
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path

from huggingface_hub import hf_hub_download
from sqlalchemy import func, select

from app.auth import hash_password
from app.config import settings
from app.db import SessionLocal
from app.deps import get_ai_provider
from app.models import (
    Agent,
    Category,
    Comment,
    Incident,
    IncidentStatus,
    KbArticle,
    KbSource,
    KbStatus,
    Priority,
    Problem,
    User,
)
from app.seed.kb_seed import KB_SEED_ARTICLES
from app.services.correlation import detect_storm
from app.services.embeddings import embed_texts

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
logging.getLogger("httpx").setLevel(logging.WARNING)
logger = logging.getLogger("helix.seed")

DATA_DIR = Path(__file__).parent / "data"
DATASET_REPO = "mindweave/help-desk-tickets"
DATASET_FILES = ["tickets.csv", "categories.csv", "agents.csv", "comments.csv"]


def _ensure_dataset_downloaded() -> None:
    """Downloads the free HuggingFace sample CSVs into DATA_DIR if not already
    cached there. DATA_DIR is gitignored, so this runs on every fresh clone."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    missing = [f for f in DATASET_FILES if not (DATA_DIR / f).exists()]
    if not missing:
        logger.info("dataset: all %d CSVs already cached in %s", len(DATASET_FILES), DATA_DIR)
        return

    logger.info("dataset: downloading %d missing file(s) from %s", len(missing), DATASET_REPO)
    for filename in missing:
        downloaded_path = hf_hub_download(
            repo_id=DATASET_REPO, repo_type="dataset", filename=f"data/{filename}"
        )
        (DATA_DIR / filename).write_bytes(Path(downloaded_path).read_bytes())
    logger.info("dataset: download complete")


STATUS_MAP = {
    "resolved": IncidentStatus.resolved,
    "closed": IncidentStatus.closed,
    "in_progress": IncidentStatus.in_progress,
    "pending": IncidentStatus.new,
}
PRIORITY_MAP = {p.value: p for p in Priority}

SEED_USERS = [
    {"email": "agent@helix.dev", "password": "helix1234", "display_name": "Alex Rivera", "team": "tier-1"},
    {"email": "lead@helix.dev", "password": "helix1234", "display_name": "Jordan Lee", "team": "tier-2"},
]

STORM_INCIDENTS = [
    (
        "VPN keeps disconnecting for the whole Denver office",
        "Since about 20 minutes ago the VPN client drops every 2-3 minutes for everyone on my floor "
        "in the Denver office. Reconnecting works briefly then it drops again.",
    ),
    (
        "Cannot stay connected to VPN - drops every few minutes",
        "My VPN connection has been unstable for the last half hour, dropping repeatedly. A "
        "coworker two desks over is having the exact same issue right now.",
    ),
    (
        "VPN gateway seems down, nobody on my team can connect",
        "Our whole team started losing VPN connectivity together around 20 minutes ago. Several of "
        "us have tried reconnecting with no luck - looks bigger than just my laptop.",
    ),
    (
        "Remote access VPN failing to connect since this morning",
        "VPN has been failing to establish a connection for the last 20 minutes. I saw in the team "
        "chat that other remote folks are hitting the same wall right now.",
    ),
    (
        "VPN connection unstable, dropping repeatedly today",
        "Getting constant VPN drops today starting about 20 minutes ago, worse than the usual "
        "occasional blip. Multiple people on my team are reporting the same thing right now.",
    ),
]


def _parse_dt(value: str) -> datetime:
    value = value.strip()
    try:
        dt = datetime.fromisoformat(value)
    except ValueError:
        head, _, frac = value.partition(".")
        dt = datetime.fromisoformat(f"{head}.{frac[:6]}" if frac else head)
    return dt if dt.tzinfo is not None else dt.replace(tzinfo=timezone.utc)


async def seed_users(db) -> None:
    existing = {u for (u,) in (await db.execute(select(User.email))).all()}
    added = 0
    for u in SEED_USERS:
        if u["email"] in existing:
            continue
        db.add(
            User(
                email=u["email"],
                password_hash=hash_password(u["password"]),
                display_name=u["display_name"],
                team=u["team"],
            )
        )
        added += 1
    logger.info("users: added %d (of %d)", added, len(SEED_USERS))


async def seed_categories(db) -> dict[str, Category]:
    with open(DATA_DIR / "categories.csv", encoding="utf-8", newline="") as f:
        rows = list(csv.DictReader(f))
    existing = {c.name: c for c in (await db.scalars(select(Category))).all()}
    added = 0
    for row in rows:
        if row["name"] in existing:
            continue
        category = Category(name=row["name"], description=f"Issues related to {row['name']} ({row['service']} service).")
        db.add(category)
        existing[row["name"]] = category
        added += 1
    await db.flush()
    logger.info("categories: added %d (of %d)", added, len(rows))
    return {row["id"]: existing[row["name"]] for row in rows}


async def seed_agents(db) -> dict[str, Agent]:
    with open(DATA_DIR / "agents.csv", encoding="utf-8", newline="") as f:
        rows = list(csv.DictReader(f))
    existing = {a.name: a for a in (await db.scalars(select(Agent))).all()}
    added = 0
    for row in rows:
        if row["name"] in existing:
            continue
        agent = Agent(name=row["name"], team=row["team"])
        db.add(agent)
        existing[row["name"]] = agent
        added += 1
    await db.flush()
    logger.info("agents: added %d (of %d)", added, len(rows))
    return {row["id"]: existing[row["name"]] for row in rows}


def _build_resolution_note(comments: list[dict], resolver_name: str) -> str:
    comments_sorted = sorted(comments, key=lambda c: c["created_at"])
    if comments_sorted:
        note = comments_sorted[-1]["body"].strip()
        if len(note) >= 20:
            return f"Resolved by {resolver_name}. {note}"
    return (
        f"Resolved by {resolver_name}. Issue addressed per standard remediation for this "
        "category; verified with the reporter before closing."
    )


async def seed_incidents(db, provider, category_by_csv_id: dict[str, Category], agent_by_csv_id: dict[str, Agent]) -> None:
    already = await db.scalar(select(func.count()).select_from(Incident))
    if already:
        logger.info("incidents: table already has %d rows, skipping ticket/comment load", already)
        return

    with open(DATA_DIR / "tickets.csv", encoding="utf-8", newline="") as f:
        tickets = list(csv.DictReader(f))
    with open(DATA_DIR / "comments.csv", encoding="utf-8", newline="") as f:
        all_comments = list(csv.DictReader(f))

    tickets.sort(key=lambda r: r["created_at"])
    selected = tickets[: settings.seed_ticket_limit]
    selected_ids = {row["ticket_id"] for row in selected}

    comments_by_ticket: dict[str, list[dict]] = defaultdict(list)
    for c in all_comments:
        if c["ticket_id"] in selected_ids:
            comments_by_ticket[c["ticket_id"]].append(c)

    unrecognized_status: set[str] = set()
    unrecognized_priority: set[str] = set()

    incidents_with_rows = []
    for i, row in enumerate(selected, start=1):
        status = STATUS_MAP.get(row["status"])
        if status is None:
            unrecognized_status.add(row["status"])
            status = IncidentStatus.new

        priority = PRIORITY_MAP.get(row["priority"])
        if priority is None:
            unrecognized_priority.add(row["priority"])

        category = category_by_csv_id.get(row["category_id"])
        agent = agent_by_csv_id.get(row["assigned_agent_id"])

        resolution_note = None
        resolved_at = None
        if status in (IncidentStatus.resolved, IncidentStatus.closed) and row.get("resolved_at"):
            resolver_name = agent.name if agent else "the assigned agent"
            resolution_note = _build_resolution_note(comments_by_ticket.get(row["ticket_id"], []), resolver_name)
            resolved_at = _parse_dt(row["resolved_at"])

        incident = Incident(
            reference=f"INC-{i:04d}",
            title=row["summary"][:200],
            description=row["description"],
            status=status,
            priority=priority,
            category_id=category.id if category else None,
            assigned_team=agent.team if agent else None,
            assigned_agent_id=agent.id if agent else None,
            reporter=row.get("requester_department") or "Unknown",
            resolution_note=resolution_note,
            resolved_at=resolved_at,
            created_at=_parse_dt(row["created_at"]),
        )
        db.add(incident)
        incidents_with_rows.append((incident, row))

    if unrecognized_status:
        logger.warning("incidents: unrecognized status values defaulted to 'new': %s", sorted(unrecognized_status))
    if unrecognized_priority:
        logger.warning("incidents: unrecognized priority values left unset: %s", sorted(unrecognized_priority))

    await db.flush()

    embeddings = await embed_texts(db, provider, [f"{inc.title}\n{inc.description}" for inc, _ in incidents_with_rows])
    for (incident, _), emb in zip(incidents_with_rows, embeddings):
        incident.embedding = emb

    comment_count = 0
    for incident, row in incidents_with_rows:
        for c in comments_by_ticket.get(row["ticket_id"], []):
            db.add(
                Comment(
                    incident_id=incident.id,
                    author=f"Agent #{c['agent_id']}" if c["agent_id"] else "System",
                    body=c["body"],
                    is_internal=c["visibility"] != "public",
                    created_at=_parse_dt(c["created_at"]),
                )
            )
            comment_count += 1

    await db.commit()
    logger.info("incidents: seeded %d incidents and %d comments", len(incidents_with_rows), comment_count)


async def seed_kb_articles(db, provider) -> None:
    existing_titles = {a.title for a in (await db.scalars(select(KbArticle))).all()}
    to_add = [a for a in KB_SEED_ARTICLES if a["title"] not in existing_titles]
    if not to_add:
        logger.info("kb_articles: already seeded, skipping")
        return

    start = (await db.scalar(select(func.count()).select_from(KbArticle))) or 0
    articles = []
    for offset, data in enumerate(to_add, start=1):
        article = KbArticle(
            reference=f"KB-{start + offset:03d}",
            title=data["title"],
            symptom=data["symptom"],
            cause=data["cause"],
            resolution_steps=data["resolution_steps"],
            verification=data["verification"],
            tags=data["tags"],
            status=KbStatus.published,
            created_by=KbSource.seed,
        )
        db.add(article)
        articles.append((article, data))
    await db.flush()

    texts = [f"{d['title']}\n{d['symptom']}\n{d['cause']}\n{d['resolution_steps']}" for _, d in articles]
    embeddings = await embed_texts(db, provider, texts)
    for (article, _), emb in zip(articles, embeddings):
        article.embedding = emb

    await db.commit()
    logger.info("kb_articles: seeded %d articles", len(articles))


async def seed_storm_cluster(db, provider, category_by_csv_id: dict[str, Category]) -> None:
    already = await db.scalar(select(func.count()).select_from(Problem))
    if already:
        logger.info("problems: table already has rows, skipping storm seed")
        return

    if not settings.ai_enabled:
        logger.warning(
            "storm seed: GEMINI_API_KEY not set, skipping synthetic VPN outage cluster - "
            "storm clustering needs real embeddings to find similar incidents"
        )
        return

    category = next((c for c in category_by_csv_id.values() if c.name == "Network & VPN"), None)
    next_id = (await db.scalar(select(func.count()).select_from(Incident))) or 0
    base_time = datetime.now(timezone.utc) - timedelta(minutes=20)

    created = []
    for i, (title, description) in enumerate(STORM_INCIDENTS):
        next_id += 1
        incident = Incident(
            reference=f"INC-{next_id:04d}",
            title=title,
            description=description,
            status=IncidentStatus.new,
            priority=Priority.P2,
            category_id=category.id if category else None,
            assigned_team="network",
            reporter="Multiple departments",
            created_at=base_time + timedelta(minutes=i * 5),
        )
        db.add(incident)
        created.append(incident)
    await db.flush()

    embeddings = await embed_texts(db, provider, [f"{i.title}\n{i.description}" for i in created])
    for incident, emb in zip(created, embeddings):
        incident.embedding = emb
    await db.flush()

    for incident in created:
        await detect_storm(db, incident, provider)
    await db.commit()
    logger.info("problems: seeded a %d-incident VPN outage storm", len(created))


async def main() -> None:
    _ensure_dataset_downloaded()

    provider = get_ai_provider()
    if not settings.ai_enabled:
        logger.warning("GEMINI_API_KEY not set - seeding will proceed without embeddings (lexical search only)")

    async with SessionLocal() as db:
        await seed_users(db)
        category_by_csv_id = await seed_categories(db)
        agent_by_csv_id = await seed_agents(db)
        await db.commit()

        await seed_incidents(db, provider, category_by_csv_id, agent_by_csv_id)
        await seed_kb_articles(db, provider)
        await seed_storm_cluster(db, provider, category_by_csv_id)

    logger.info("Seed complete.")


if __name__ == "__main__":
    asyncio.run(main())
