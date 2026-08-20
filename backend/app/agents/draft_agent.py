from typing import Any

from app.facts import normalize_facts


def create_draft(extracted_facts: list[dict[str, Any]], conflicts: list[dict[str, Any]]) -> dict[str, Any]:
    facts = normalize_facts(extracted_facts)
    milestones: dict[str, dict[str, Any]] = {}
    for fact in facts:
        if fact.get("category") != "milestone" or not fact.get("subject"):
            continue
        subject = str(fact["subject"]).strip()
        key = subject.casefold()
        item = milestones.setdefault(key, {
            "subject": subject, "due_date": None, "owner": None,
            "source_document": None, "evidence": None,
        })
        fact_type = fact.get("fact_type")
        if fact_type in {"due_date", "owner"} and fact.get("value") is not None:
            item[fact_type] = fact.get("value")
            # Keep evidence paired with the value most recently used. Individual
            # attributes retain their evidence in facts for complete traceability.
            item["source_document"] = fact.get("source_document") or fact.get("filename")
            item["evidence"] = fact.get("evidence")
    return {
        "milestones": list(milestones.values()),
        "owners": [f for f in facts if f.get("category") == "owners"],
        "dates": [f for f in facts if f.get("category") == "dates"],
        "risks": [f for f in facts if f.get("category") == "risks"],
        "decisions": [f for f in facts if f.get("category") == "decisions"],
        "action_items": [f for f in facts if f.get("category") == "action_items"],
        "facts": facts,
        "conflicts": conflicts,
    }
