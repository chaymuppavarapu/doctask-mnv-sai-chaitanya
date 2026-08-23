import re
import uuid
from typing import Any


def compare_facts(facts: list[dict[str, Any]]) -> list[dict[str, Any]]:
    conflicts: list[dict[str, Any]] = []

    def make_key(fact: dict[str, Any]) -> tuple[str | None, str | None, str | None]:
        subject = (fact.get("subject") or "").strip().lower() or None
        fact_type = (fact.get("fact_type") or "").strip().lower() or None
        category = (fact.get("category") or "").strip().lower() or None
        return subject, fact_type, category

    grouped: dict[tuple[str | None, str | None, str | None], list[dict[str, Any]]] = {}
    for f in facts:
        # Narrative risks/decisions are multi-valued by design.  Only compare
        # scalar attributes for contradictory values requiring human choice.
        if (f.get("fact_type") or "").strip().lower() not in {"due_date", "owner", "budget", "scope"}:
            continue
        key = make_key(f)
        grouped.setdefault(key, []).append(f)

    for key, entries in grouped.items():
        if len(entries) < 2:
            continue

        unique_values: dict[Any, list[dict[str, Any]]] = {}
        for entry in entries:
            normalized = entry.get("normalized_value", entry.get("value"))
            unique_values.setdefault(normalized, []).append(entry)

        distinct_values = [value for value in unique_values.keys() if value is not None]
        if len(distinct_values) < 2:
            continue

        current_entries = [e for e in entries if e.get("temporal_status") == "current"]
        historical_entries = [e for e in entries if e.get("temporal_status") == "historical"]
        conflict_type = "contradiction"
        if current_entries and historical_entries:
            current_values = {e.get("normalized_value", e.get("value")) for e in current_entries}
            historical_values = {e.get("normalized_value", e.get("value")) for e in historical_entries}
            if len(current_values) == 1 and historical_values and current_values != historical_values:
                conflict_type = "historical_change"
        elif len(current_entries) > 1:
            conflict_type = "contradiction"
        else:
            conflict_type = "ambiguous"

        v1 = distinct_values[0]
        v2 = distinct_values[1]
        fa = unique_values[v1][0]
        fb = unique_values[v2][0]

        description_parts = []
        if key[0]:
            description_parts.append(f"subject '{key[0]}'")
        if key[1]:
            description_parts.append(f"fact type '{key[1]}'")
        if key[2]:
            description_parts.append(f"category '{key[2]}'")
        description = "Conflicting facts for " + ", ".join(description_parts) if description_parts else "Conflicting extracted facts"

        conflicts.append({
            "conflict_id": str(uuid.uuid4()),
            "description": description,
            "conflict_type": conflict_type,
            "fact_a": v1,
            "source_a": fa.get("source_document") or fa.get("filename"),
            "evidence_a": fa.get("evidence"),
            "fact_b": v2,
            "source_b": fb.get("source_document") or fb.get("filename"),
            "evidence_b": fb.get("evidence"),
            "status": "pending_review",
        })

    return conflicts
