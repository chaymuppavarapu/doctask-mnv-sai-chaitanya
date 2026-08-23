import json
import re
import time
from datetime import datetime
from typing import Any

from app.config import settings
from groq import Groq

DEFAULT_GROQ_MODEL = "openai/gpt-oss-120b"

FACTS_RESPONSE_SCHEMA = {
    "type": "object",
    "properties": {
        "facts": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "subject": {"type": "string"},
                    "fact_type": {"type": "string"},
                    "value": {"type": "string"},
                    "normalized_value": {"type": "string"},
                    "value_type": {"type": "string"},
                    "temporal_status": {"type": "string"},
                    "source_document": {"type": "string"},
                    "evidence": {"type": "string"}
                },
                "required": [
                    "subject",
                    "fact_type",
                    "value",
                    "normalized_value",
                    "value_type",
                    "temporal_status",
                    "source_document",
                    "evidence",
                ],
                "additionalProperties": False
            }
        }
    },
    "required": ["facts"],
    "additionalProperties": False
}

CURRENCY_SYMBOLS = {
    "$": "USD",
    "€": "EUR",
    "£": "GBP",
    "¥": "JPY",
}

DATE_FORMATS = [
    "%Y-%m-%d",
    "%B %d, %Y",
    "%b %d, %Y",
    "%B %d %Y",
    "%b %d %Y",
    "%d %B %Y",
    "%d %b %Y",
    "%m/%d/%Y",
    "%m-%d-%Y",
]


def _get_groq_client() -> Any:
    if not settings.groq_api_key:
        raise ValueError("GROQ_API_KEY is required for fact extraction")
    return Groq(api_key=settings.groq_api_key)


def _normalize_date(value: str) -> str | None:
    if not isinstance(value, str):
        return None
    text = re.sub(r"\b(st|nd|rd|th)\b", "", value, flags=re.IGNORECASE).strip()
    for fmt in DATE_FORMATS:
        try:
            return datetime.strptime(text, fmt).date().isoformat()
        except ValueError:
            continue
    return None


def _normalize_number(value: str) -> int | float | None:
    if not isinstance(value, str):
        return None
    cleaned = value.strip().replace(",", "")
    if re.fullmatch(r"[+-]?\d+", cleaned):
        return int(cleaned)
    if re.fullmatch(r"[+-]?\d+\.\d+", cleaned):
        try:
            return float(cleaned)
        except ValueError:
            return None
    return None


def _normalize_value(value: Any) -> tuple[Any, str | None]:
    if isinstance(value, (int, float)):
        return value, "number"

    if isinstance(value, str):
        text = value.strip()
        if not text:
            return text, "text"

        percent_match = re.search(r"([+-]?\d+(?:\.\d+)?)\s*%", text)
        if percent_match:
            number_text = percent_match.group(1)
            normalized = float(number_text) if "." in number_text else int(number_text)
            return normalized, "percentage"

        currency_match = re.search(r"(?P<symbol>[\$€£¥])\s*(?P<amount>[0-9][0-9,]*(?:\.[0-9]+)?)", text)
        if currency_match:
            symbol = currency_match.group("symbol")
            amount_text = currency_match.group("amount").replace(",", "")
            amount = float(amount_text) if "." in amount_text else int(amount_text)
            code = CURRENCY_SYMBOLS.get(symbol, symbol)
            return f"{code} {amount}", "currency"

        iso_date = _normalize_date(text)
        if iso_date:
            return iso_date, "date"

        numeric = _normalize_number(text)
        if numeric is not None:
            return numeric, "number"

        return text, "text"

    return value, None


def _extract_response_text(response: Any) -> str:
    if hasattr(response, "output_text"):
        return response.output_text
    if isinstance(response, dict):
        if "output_text" in response:
            return response["output_text"]
        output = response.get("output")
    else:
        output = getattr(response, "output", None)

    if hasattr(response, "choices") and response.choices:
        first_choice = response.choices[0]
        if hasattr(first_choice, "message"):
            message = first_choice.message
            if hasattr(message, "content"):
                return str(message.content)

    if isinstance(output, list) and output:
        first = output[0]
        if isinstance(first, dict):
            content = first.get("content")
            if isinstance(content, list):
                return "".join(str(item.get("text", "")) for item in content if isinstance(item, dict))
            if isinstance(content, str):
                return content
        if isinstance(first, str):
            return first

    if isinstance(response, str):
        return response

    return json.dumps(response)


def _extract_json_payload(raw: str) -> dict[str, Any]:
    raw = raw.strip()
    if not raw:
        raise ValueError("Groq response is empty")

    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        start = raw.find("{")
        end = raw.rfind("}")
        if start == -1 or end == -1:
            raise
        return json.loads(raw[start : end + 1])


def _read_attr_or_key(value: Any, key: str) -> Any:
    if isinstance(value, dict):
        return value.get(key)
    return getattr(value, key, None)


def _read_int(value: Any) -> int | None:
    if value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _estimate_cost(input_tokens: int | None, output_tokens: int | None) -> float | None:
    if input_tokens is None or output_tokens is None:
        return None
    if settings.llm_input_cost_per_1m is None or settings.llm_output_cost_per_1m is None:
        return None
    cost = (
        (input_tokens * settings.llm_input_cost_per_1m)
        + (output_tokens * settings.llm_output_cost_per_1m)
    ) / 1_000_000
    return round(cost, 8)


def _metrics_from_response(response: Any, model: str, duration_ms: int, status: str = "completed", error: str | None = None) -> dict[str, Any]:
    usage = _read_attr_or_key(response, "usage") if response is not None else None
    x_groq = _read_attr_or_key(response, "x_groq") if response is not None else None
    x_usage = _read_attr_or_key(x_groq, "usage") if x_groq is not None else None
    usage = usage or x_usage

    input_tokens = _read_int(_read_attr_or_key(usage, "prompt_tokens"))
    output_tokens = _read_int(_read_attr_or_key(usage, "completion_tokens"))
    total_tokens = _read_int(_read_attr_or_key(usage, "total_tokens"))
    if total_tokens is None and input_tokens is not None and output_tokens is not None:
        total_tokens = input_tokens + output_tokens

    response_model = _read_attr_or_key(response, "model") if response is not None else None

    return {
        "status": status,
        "model": response_model or model,
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "total_tokens": total_tokens,
        "duration_ms": duration_ms,
        "estimated_cost": _estimate_cost(input_tokens, output_tokens),
        "error": error,
    }


def _error_metrics(model: str, started: float, error: Exception) -> dict[str, Any]:
    return _metrics_from_response(
        None,
        model,
        int((time.perf_counter() - started) * 1000),
        status="error",
        error=str(error),
    )


def _build_prompt(chunks: list[dict[str, Any]], query: str | None = None) -> str:
    evidence_blocks = []
    for index, chunk in enumerate(chunks, start=1):
        source = chunk.get("source_filename", "unknown")
        text = (chunk.get("text") or "").strip()
        if not text:
            continue
        evidence_blocks.append(
            f"Source document: {source}\nChunk {index}:\n{text}"
        )

    evidence_text = "\n\n".join(evidence_blocks).strip()
    query_text = f"Query: {query}\n\n" if query else ""

    return (
        "You are a project-document fact extraction agent. Analyze ONLY the supplied evidence. "
        "Do not invent facts or use outside knowledge. Do not assume a fixed document format, headings, or terminology. "
        "Identify meaningful factual information stated in the evidence. Normalize values when unambiguous. "
        "Preserve source document and exact supporting evidence. Distinguish current and historical information when present. "
        "Return a JSON object with a single key \"facts\" containing an array of fact objects. "
        "Each fact object may include: subject, fact_type, value, normalized_value, value_type, temporal_status, source_document, evidence. "
        "If a fact cannot be extracted clearly, omit it. "
        "Do not include any other keys. Return only valid JSON, no markdown.\n\n"
        f"{query_text}"
        "Evidence:\n"
        f"{evidence_text}\n"
    )


def _validate_fact(raw_fact: Any) -> dict[str, Any]:
    if not isinstance(raw_fact, dict):
        raise ValueError("Each fact must be a JSON object")

    source_document = raw_fact.get("source_document")
    evidence = raw_fact.get("evidence")
    value = raw_fact.get("value")

    if not source_document or not evidence or value is None:
        raise ValueError("Each extracted fact must include source_document, evidence, and value")

    fact: dict[str, Any] = {
        "source_document": source_document,
        "evidence": evidence,
        "value": value,
        "normalized_value": raw_fact.get("normalized_value"),
        "value_type": raw_fact.get("value_type"),
        "temporal_status": raw_fact.get("temporal_status", "unknown"),
    }

    if subject := raw_fact.get("subject"):
        fact["subject"] = str(subject).strip()
    if fact_type := raw_fact.get("fact_type"):
        normalized_fact_type = str(fact_type).strip()
        if normalized_fact_type.lower() in ("milestone_due_date", "milestone due date"):
            normalized_fact_type = "due_date"
        elif normalized_fact_type.lower() in ("milestone_owner", "milestone owner"):
            normalized_fact_type = "owner"
        fact["fact_type"] = normalized_fact_type
    if category := raw_fact.get("category"):
        fact["category"] = str(category).strip()
    else:
        # Providers occasionally omit an optional semantic label despite
        # otherwise valid evidence.  Keep the extraction usable and grounded.
        inferred_category = {
            "due_date": "milestone",
            "owner": "owner",
            "risk": "risk",
            "status": "status",
            "decision": "decision",
            "action_item": "action_item",
        }.get(str(fact.get("fact_type") or "").lower(), "fact")
        fact["category"] = inferred_category

    if fact["normalized_value"] is None:
        normalized, inferred_type = _normalize_value(value)
        fact["normalized_value"] = normalized
        if fact["value_type"] is None and inferred_type is not None:
            fact["value_type"] = inferred_type
    elif fact["value_type"] is None:
        _, inferred_type = _normalize_value(fact["normalized_value"])
        fact["value_type"] = inferred_type

    if not fact.get("temporal_status"):
        fact["temporal_status"] = "unknown"

    return fact


def extract_facts_from_chunks(
    chunks: list[dict[str, Any]],
    query: str | None = None,
    return_metrics: bool = False,
) -> list[dict[str, Any]] | tuple[list[dict[str, Any]], dict[str, Any] | None]:
    if not chunks:
        return ([], None) if return_metrics else []

    prompt = _build_prompt(chunks, query=query)
    model = settings.groq_model or DEFAULT_GROQ_MODEL
    response = None
    started = time.perf_counter()
    try:
        client = _get_groq_client()
        response = client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            response_format={
                "type": "json_schema",
                "json_schema": {
                    "name": "doctask_facts",
                    "schema": FACTS_RESPONSE_SCHEMA,
                    "strict": True,
                },
            },
            reasoning_format="hidden",
            reasoning_effort="low",
            temperature=0,
            max_completion_tokens=2048,
        )
        duration_ms = int((time.perf_counter() - started) * 1000)
        metrics = _metrics_from_response(response, model, duration_ms)
        raw_text = _extract_response_text(response)
        payload = _extract_json_payload(raw_text)

        facts = payload.get("facts")
        if not isinstance(facts, list):
            raise ValueError("Groq extraction did not return a facts array")

        validated_facts = []
        for raw_fact in facts:
            validated_facts.append(_validate_fact(raw_fact))

        return (validated_facts, metrics) if return_metrics else validated_facts
    except Exception as exc:
        metrics = _metrics_from_response(
            response,
            model,
            int((time.perf_counter() - started) * 1000),
            status="error",
            error=str(exc),
        ) if response is not None else _error_metrics(model, started, exc)
        setattr(exc, "llm_metrics", metrics)
        raise
