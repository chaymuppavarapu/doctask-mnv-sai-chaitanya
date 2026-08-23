"""Small, provider-independent helpers for facts used by every workflow stage."""
from __future__ import annotations

from typing import Any
import re


_FACT_TYPE_ALIASES = {
    "due date": "due_date",
    "milestone_due_date": "due_date",
    "milestone due date": "due_date",
    "due": "due_date",
    "deadline": "due_date",
    "completion date": "completion_date",
    "milestone_completion_date": "completion_date",
    "milestone completion date": "completion_date",
    "milestone_owner": "owner",
    "milestone owner": "owner",
}

_MILESTONE_SUBJECT_SUFFIX = re.compile(
    r"\s+(?:milestone\s+)?(?:owner|completion(?:\s+date)?|status)\s*$",
    re.IGNORECASE,
)
_DOCUMENT_PREFIX = re.compile(
    r"^(?:project\s+update|status\s+update|week\s+\d+\s+status)\s+",
    re.IGNORECASE,
)


def _canonical_milestone_subject(subject: str) -> tuple[str, bool]:
    """Return a logical milestone subject and whether a suffix established it."""
    cleaned = subject.strip()
    while True:
        updated = _DOCUMENT_PREFIX.sub("", cleaned).strip()
        if updated == cleaned:
            break
        cleaned = updated
    cleaned = re.sub(r"^the\s+", "", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"\s+milestone\s*$", "", cleaned, flags=re.IGNORECASE)
    parent = _MILESTONE_SUBJECT_SUFFIX.sub("", cleaned).strip()
    return parent, parent != cleaned


def _is_explicit_milestone_evidence(evidence: Any) -> bool:
    return isinstance(evidence, str) and bool(re.search(r"\bmilestones?\b", evidence, re.IGNORECASE))


def normalize_fact(fact: dict[str, Any]) -> dict[str, Any]:
    """Return a canonical fact without inventing missing evidence or values."""
    result = dict(fact)
    subject_has_milestone_suffix = False
    if isinstance(result.get("subject"), str):
        # Keep source/evidence intact while using one internal logical subject.
        result["subject"], subject_has_milestone_suffix = _canonical_milestone_subject(result["subject"])
    fact_type = str(result.get("fact_type") or "").strip().lower()
    if fact_type:
        fact_type = _FACT_TYPE_ALIASES.get(fact_type, fact_type)
        result["fact_type"] = fact_type

    category = str(result.get("category") or "").strip().lower()
    if category in {"milestones", "milestone"}:
        result["category"] = "milestone"
    elif result.get("subject") and (
        # A due date is an unambiguous dated attribute of its named subject.
        fact_type == "due_date"
        # Owner/completion/status facts need an explicit milestone signal so a
        # risk owner or unrelated status cannot be reclassified accidentally.
        or (
            fact_type in {"owner", "completion_date", "status"}
            and (
                category in {"dates", "owners"}
                or subject_has_milestone_suffix
                or _is_explicit_milestone_evidence(result.get("evidence"))
            )
        )
    ):
        result["category"] = "milestone"
    return result


def normalize_facts(facts: list[dict[str, Any]] | None) -> list[dict[str, Any]]:
    return [normalize_fact(fact) for fact in (facts or []) if isinstance(fact, dict)]
