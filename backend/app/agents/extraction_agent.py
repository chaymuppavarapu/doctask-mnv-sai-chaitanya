import re
from datetime import datetime
from typing import Any

from app.groq_client import extract_facts_from_chunks


def extract_facts_from_contexts(
    retrieved_contexts: list[dict[str, Any]],
    query: str | None = None,
    include_metrics: bool = False,
) -> list[dict[str, Any]] | tuple[list[dict[str, Any]], dict[str, Any] | None]:
    return extract_facts_from_chunks(retrieved_contexts, query=query, return_metrics=include_metrics)


def extract_structured_milestone_facts(contexts: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Evidence-only fallback for common numbered milestone blocks.

    It complements provider output rather than interpreting instructions in documents.
    """
    results: list[dict[str, Any]] = []
    month = r"(?:Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|Jul(?:y)?|Aug(?:ust)?|Sep(?:t(?:ember)?)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?)"
    date_text = rf"{month}\s+\d{{1,2}}(?:,\s*\d{{4}})?"

    def normalize_date(text: str, fallback_year: str | None = None) -> str:
        candidate = text.strip()
        if not re.search(r"\d{4}", candidate) and fallback_year:
            candidate = f"{candidate}, {fallback_year}"
        for fmt in ("%B %d, %Y", "%b %d, %Y", "%B %d %Y", "%b %d %Y"):
            try:
                return datetime.strptime(candidate.replace(",", ""), fmt.replace(",", "")).date().isoformat()
            except ValueError:
                continue
        return candidate

    block = re.compile(
        r"(?:^|\s)(?:\d+\.\s+)(?P<subject>[A-Za-z][A-Za-z ]{1,100}?)\s+Owner:\s*(?P<owner>[A-Za-z][A-Za-z .'-]*)\s+Due:\s*(?P<due>[A-Za-z]+\s+\d{1,2},\s*\d{4})",
        re.IGNORECASE,
    )
    moved = re.compile(
        rf"(?:The\s+)?(?P<subject>[A-Za-z][A-Za-z ]{{1,100}}?)\s+milestone\s+was\s+moved\s+from\s+(?P<old>{date_text})\s+to\s+(?P<new>{date_text})",
        re.IGNORECASE,
    )
    for context in contexts:
        text = context.get("text") or ""
        source = context.get("source_filename") or "unknown"
        for match in block.finditer(text):
            subject = match.group("subject").strip()
            due = match.group("due").strip()
            normalized_due = normalize_date(due)
            evidence = match.group(0).strip()
            results.extend([
                {"subject": subject, "fact_type": "due_date", "value": due, "normalized_value": normalized_due,
                 "value_type": "date", "temporal_status": "current", "source_document": source, "evidence": evidence, "category": "milestone"},
                {"subject": subject, "fact_type": "owner", "value": match.group("owner").strip(), "normalized_value": match.group("owner").strip(),
                 "value_type": "person", "temporal_status": "current", "source_document": source, "evidence": evidence, "category": "milestone"},
            ])
        for match in moved.finditer(text):
            subject = match.group("subject").strip()
            old_due = match.group("old").strip()
            new_due = match.group("new").strip()
            year_match = re.search(r"\b(\d{4})\b", new_due) or re.search(r"\b(\d{4})\b", old_due)
            year = year_match.group(1) if year_match else None
            evidence = match.group(0).strip()
            results.extend([
                {"subject": subject, "fact_type": "due_date", "value": old_due, "normalized_value": normalize_date(old_due, year),
                 "value_type": "date", "temporal_status": "historical", "source_document": source, "evidence": evidence, "category": "milestone"},
                {"subject": subject, "fact_type": "due_date", "value": new_due, "normalized_value": normalize_date(new_due, year),
                 "value_type": "date", "temporal_status": "current", "source_document": source, "evidence": evidence, "category": "milestone"},
            ])
    return results
