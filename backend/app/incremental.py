"""Helpers for targeted incremental analysis updates.

The incremental path keeps the previously accepted facts intact, reprocesses
only the newly added evidence, and compares the new facts only against the
existing facts for the same subject/fact-type keys.
"""
from __future__ import annotations

import copy
import uuid
from datetime import datetime
from typing import Any

from app.agents.conflict_agent import compare_facts
from app.agents.draft_agent import create_draft
from app.facts import normalize_facts
from app.models.change_record import ChangeRecord


def _fact_key(fact: dict[str, Any]) -> tuple[str, str]:
    subject = str(fact.get("subject") or "").strip().casefold()
    fact_type = str(fact.get("fact_type") or "").strip().casefold()
    return subject, fact_type


def _value_key(fact: dict[str, Any]) -> str:
    value = fact.get("normalized_value", fact.get("value"))
    return str(value).strip().casefold() if value is not None else ""


def _fact_signature(fact: dict[str, Any]) -> tuple[str, str, str]:
    source = str(fact.get("source_document") or fact.get("filename") or "").strip().casefold()
    evidence = str(fact.get("evidence") or "").strip().casefold()
    return (*_fact_key(fact), f"{_value_key(fact)}|{source}|{evidence}")


def _subject_key(subject: Any) -> str:
    if not isinstance(subject, str) or not subject.strip():
        return ""
    normalized = normalize_facts([{"subject": subject}])
    return str(normalized[0].get("subject") or "").strip().casefold() if normalized else ""


def select_affected_base_facts(base_facts: list[dict[str, Any]], new_facts: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Return only the existing facts that a new document could affect."""
    normalized_base = normalize_facts(base_facts)
    impacted_keys = {_fact_key(fact) for fact in normalize_facts(new_facts)}
    return [fact for fact in normalized_base if _fact_key(fact) in impacted_keys]


def merge_incremental_facts(
    base_facts: list[dict[str, Any]],
    new_facts: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    """Merge a new evidence set over an accepted fact baseline.

    Unaffected facts are copied exactly from the baseline. New facts are only
    appended when they introduce a new subject/fact-type value. When the same
    key appears with a different value, both values are preserved and the
    comparison output carries a conflict for human review.
    """
    normalized_base = normalize_facts(base_facts)
    normalized_new = normalize_facts(new_facts)

    merged: list[dict[str, Any]] = [copy.deepcopy(fact) for fact in normalized_base]
    seen_signatures = {_fact_signature(fact) for fact in merged}
    base_values = {_fact_key(fact): _value_key(fact) for fact in normalized_base}
    base_keys = set(base_values)
    new_by_key: dict[tuple[str, str], list[dict[str, Any]]] = {}
    for fact in normalized_new:
        new_by_key.setdefault(_fact_key(fact), []).append(fact)

    conflicts: list[dict[str, Any]] = []
    affected_base: list[dict[str, Any]] = []

    for key, related_new in new_by_key.items():
        related_base = [fact for fact in normalized_base if _fact_key(fact) == key]
        if related_base:
            affected_base.extend(related_base)

        key_conflicts = compare_facts(related_base + related_new) if related_base else []
        if key_conflicts:
            conflicts.extend(key_conflicts)
        elif related_base:
            base_fact = related_base[0]
            for new_fact in related_new:
                if base_values.get(key) != _value_key(new_fact):
                    conflicts.append({
                        "conflict_id": str(uuid.uuid4()),
                        "description": (
                            "Conflicting facts for subject "
                            f"'{base_fact.get('subject')}'" if base_fact.get("subject") else "Conflicting facts"
                        ),
                        "conflict_type": "contradiction",
                        "fact_a": base_fact.get("normalized_value", base_fact.get("value")),
                        "source_a": base_fact.get("source_document") or base_fact.get("filename"),
                        "evidence_a": base_fact.get("evidence"),
                        "fact_b": new_fact.get("normalized_value", new_fact.get("value")),
                        "source_b": new_fact.get("source_document") or new_fact.get("filename"),
                        "evidence_b": new_fact.get("evidence"),
                        "status": "pending_review",
                    })

    for fact in normalized_new:
        signature = _fact_signature(fact)
        if signature in seen_signatures:
            continue

        key = _fact_key(fact)
        value = _value_key(fact)
        if key in base_keys and base_values.get(key) == value:
            continue

        merged.append(copy.deepcopy(fact))
        seen_signatures.add(signature)

    return merged, conflicts, affected_base


def record_incremental_fact_changes(
    db,
    project_id: int,
    base_facts: list[dict[str, Any]],
    new_facts: list[dict[str, Any]],
) -> None:
    """Append audit records for the facts touched by the incremental update."""
    normalized_base = normalize_facts(base_facts)
    normalized_new = normalize_facts(new_facts)
    base_by_key = {_fact_key(fact): fact for fact in normalized_base}

    for fact in normalized_new:
        key = _fact_key(fact)
        if key == ("", ""):
            continue

        base_fact = base_by_key.get(key)
        old_value = base_fact.get("normalized_value", base_fact.get("value")) if base_fact else None
        new_value = fact.get("normalized_value", fact.get("value"))
        if base_fact is not None and str(old_value).strip().casefold() == str(new_value).strip().casefold():
            continue

        db.add(
            ChangeRecord(
                project_id=project_id,
                subject=fact.get("subject"),
                fact_type=fact.get("fact_type") or "fact",
                old_value={"value": old_value} if old_value is not None else None,
                new_value={"value": new_value},
                source_document=fact.get("source_document") or fact.get("filename"),
                review_status="pending_review" if base_fact is not None else "recorded",
                created_at=datetime.utcnow(),
            )
        )

    db.commit()


def build_incremental_draft(
    base_draft: dict[str, Any] | None,
    current_facts: list[dict[str, Any]],
    conflicts: list[dict[str, Any]],
    changed_facts: list[dict[str, Any]],
) -> dict[str, Any]:
    """Preserve the completed baseline draft and patch only touched subjects."""
    preserved = copy.deepcopy(base_draft) if isinstance(base_draft, dict) else {}
    rebuilt = create_draft(current_facts, conflicts)
    touched_subjects = {
        _subject_key(fact.get("subject"))
        for fact in normalize_facts(changed_facts)
        if _subject_key(fact.get("subject"))
    }

    if not touched_subjects:
        if "milestones" not in preserved:
            preserved["milestones"] = rebuilt.get("milestones", [])
    else:
        existing = list(preserved.get("milestones", [])) if isinstance(preserved.get("milestones"), list) else []
        changed_attributes: dict[str, dict[str, dict[str, Any]]] = {}
        for fact in normalize_facts(changed_facts):
            key = _subject_key(fact.get("subject"))
            if not key:
                continue
            fact_type = str(fact.get("fact_type") or "").strip().casefold()
            changed_attributes.setdefault(key, {})[fact_type] = copy.deepcopy(fact)

        rebuilt_by_subject = {}
        for item in rebuilt.get("milestones", []):
            if not isinstance(item, dict):
                continue
            key = _subject_key(item.get("subject"))
            if key not in touched_subjects:
                continue
            patched_item = copy.deepcopy(item)
            changed_due = changed_attributes.get(key, {}).get("due_date")
            changed_owner = changed_attributes.get(key, {}).get("owner")
            if changed_due and changed_due.get("value") is not None:
                patched_item["due_date"] = changed_due.get("value")
                patched_item["source_document"] = changed_due.get("source_document") or changed_due.get("filename")
                patched_item["evidence"] = changed_due.get("evidence")
            elif changed_owner and changed_owner.get("value") is not None:
                patched_item["owner"] = changed_owner.get("value")
                patched_item["source_document"] = changed_owner.get("source_document") or changed_owner.get("filename")
                patched_item["evidence"] = changed_owner.get("evidence")
            rebuilt_by_subject[key] = patched_item

        merged_milestones: list[dict[str, Any]] = []
        seen_subjects: set[str] = set()
        for item in existing:
            if not isinstance(item, dict):
                continue
            key = _subject_key(item.get("subject"))
            if key and key in touched_subjects:
                replacement = rebuilt_by_subject.get(key)
                merged_milestones.append(copy.deepcopy(replacement) if replacement is not None else copy.deepcopy(item))
                seen_subjects.add(key)
            else:
                merged_milestones.append(copy.deepcopy(item))

        for key, item in rebuilt_by_subject.items():
            if key not in seen_subjects:
                merged_milestones.append(copy.deepcopy(item))

        preserved["milestones"] = merged_milestones

    preserved["facts"] = rebuilt.get("facts", normalize_facts(current_facts))
    preserved["conflicts"] = copy.deepcopy(conflicts)
    return preserved



