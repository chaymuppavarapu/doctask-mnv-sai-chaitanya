from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text, func

from app.db import SessionLocal
from app.db import create_tables
from fastapi import UploadFile, File, Form, HTTPException, status
from fastapi.responses import JSONResponse
from app.models.document import Document
from app.models.project import Project
from app.models.run import Run
from app.models.change_record import ChangeRecord
from app.semantic import search, retrieve_relevant_chunks, index_document_chunks
from app.agents.extraction_agent import extract_facts_from_contexts, extract_structured_milestone_facts
from app.agents.conflict_agent import compare_facts
from app.agents.draft_agent import create_draft
from app.agents.examine_agent import examine_run
from app.facts import normalize_facts
from app.incremental import build_incremental_draft, merge_incremental_facts, record_incremental_fact_changes, select_affected_base_facts
from fastapi import Body
from fastapi.responses import PlainTextResponse
import re
import copy
from datetime import datetime, timedelta
import uuid
import json
import traceback
from fastapi.testclient import TestClient
from typing import Any, List
from langchain_core.runnables import RunnableConfig
from fastapi import Depends
from langgraph import graph
from sqlalchemy import desc

try:
    from PyPDF2 import PdfReader
except Exception:
    PdfReader = None

try:
    from docx import Document as DocxDocument
except Exception:
    DocxDocument = None

app = FastAPI(title="Project Intelligence System")


def _record_document_added(db, project_id: int, document: Document) -> None:
    """Persist ingestion as a non-destructive incremental change event."""
    db.add(ChangeRecord(
        project_id=project_id,
        subject=None,
        fact_type="document_added",
        old_value=None,
        new_value={"document_id": document.id, "filename": document.filename},
        source_document=document.filename,
        review_status="pending_analysis",
    ))
    db.commit()


def _record_fact_changes(db, project_id: int, previous_facts: list[dict[str, Any]], current_facts: list[dict[str, Any]]) -> None:
    """Record only changed subject/type values; unchanged evidence is preserved."""
    def key(fact):
        return (str(fact.get("subject") or "").casefold(), str(fact.get("fact_type") or "").casefold())
    previous = {key(f): f for f in previous_facts if isinstance(f, dict) and key(f) != ("", "")}
    current = {key(f): f for f in current_facts if isinstance(f, dict) and key(f) != ("", "")}
    for fact_key, new_fact in current.items():
        old_fact = previous.get(fact_key)
        old_value = old_fact.get("normalized_value", old_fact.get("value")) if old_fact else None
        new_value = new_fact.get("normalized_value", new_fact.get("value"))
        if old_fact and old_value == new_value:
            continue
        db.add(ChangeRecord(
            project_id=project_id, subject=new_fact.get("subject"), fact_type=new_fact.get("fact_type") or "fact",
            old_value={"value": old_value} if old_fact else None,
            new_value={"value": new_value}, source_document=new_fact.get("source_document") or new_fact.get("filename"),
            review_status="recorded",
        ))
    db.commit()

# Minimal CORS for local Vite dev server
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Content-Type"],
)


@app.on_event("startup")
def startup():
    create_tables()

@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/health/db")
def database_health():
    db = SessionLocal()

    try:
        db.execute(text("SELECT 1"))
        return {"status": "ok", "database": "connected"}
    finally:
        db.close()


@app.post("/projects")
def create_project(body: dict = Body(...)):
    name = body.get("name")
    if not name or not isinstance(name, str):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Project name is required")

    db = SessionLocal()
    try:
        existing = db.query(Project).filter(Project.name == name).first()
        if existing:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Project name already exists")

        project = Project(name=name)
        db.add(project)
        db.commit()
        db.refresh(project)

        return JSONResponse(status_code=201, content={
            "id": project.id,
            "name": project.name,
            "created_at": project.created_at.isoformat() if project.created_at else None,
        })
    finally:
        db.close()


@app.get("/projects")
def list_projects():
    db = SessionLocal()
    try:
        rows = (
            db.query(Project, func.count(Document.id).label("document_count"))
            .outerjoin(Document)
            .group_by(Project.id)
            .order_by(Project.created_at.desc())
            .all()
        )

        results = []
        for project, document_count in rows:
            results.append({
                "id": project.id,
                "name": project.name,
                "created_at": project.created_at.isoformat() if project.created_at else None,
                "document_count": document_count,
            })
        return JSONResponse(status_code=200, content=results)
    finally:
        db.close()


@app.get("/projects/{project_id}")
def get_project(project_id: int):
    db = SessionLocal()
    try:
        project = db.query(Project).filter(Project.id == project_id).first()
        if not project:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")

        document_count = db.query(Document).filter(Document.project_id == project.id).count()
        return JSONResponse(status_code=200, content={
            "id": project.id,
            "name": project.name,
            "created_at": project.created_at.isoformat() if project.created_at else None,
            "document_count": document_count,
        })
    finally:
        db.close()


@app.get("/projects/{project_id}/documents")
def list_project_documents(project_id: int):
    db = SessionLocal()
    try:
        project = db.query(Project).filter(Project.id == project_id).first()
        if not project:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")

        docs: List[Document] = (
            db.query(Document)
            .filter(Document.project_id == project_id)
            .order_by(desc(Document.uploaded_at))
            .all()
        )

        results = []
        for d in docs:
            results.append({
                "id": d.id,
                "filename": d.filename,
                "document_type": d.document_type,
                "status": "uploaded",
                "uploaded_at": d.uploaded_at.isoformat() if d.uploaded_at is not None else None,
            })
        return JSONResponse(status_code=200, content=results)
    finally:
        db.close()


def _extract_file_text(file: UploadFile, filename: str) -> str:
    lower = filename.lower()
    if lower.endswith(".txt") or file.content_type.startswith("text"):
        raw = file.file.read()
        try:
            return raw.decode("utf-8")
        except Exception:
            try:
                return raw.decode("latin-1")
            except Exception:
                raise HTTPException(status_code=415, detail="Unable to decode text file")

    if lower.endswith(".pdf") or file.content_type == "application/pdf":
        if PdfReader is None:
            raise HTTPException(status_code=500, detail="PDF support not available (missing PyPDF2)")
        try:
            reader = PdfReader(file.file)
            texts = []
            for page in reader.pages:
                page_text = page.extract_text()
                if page_text:
                    texts.append(page_text)
            return "\n".join(texts)
        except Exception as e:
            raise HTTPException(status_code=415, detail=f"Failed to extract PDF text: {e}")

    if lower.endswith(".docx"):
        if DocxDocument is None:
            raise HTTPException(status_code=500, detail="DOCX support not available (missing python-docx)")
        try:
            doc = DocxDocument(file.file)
            return "\n".join([p.text for p in doc.paragraphs if p.text])
        except Exception as e:
            raise HTTPException(status_code=415, detail=f"Failed to extract DOCX text: {e}")

    raise HTTPException(status_code=415, detail="Unsupported file type")


@app.post("/projects/{project_id}/documents/upload")
def upload_project_documents(project_id: int, files: list[UploadFile] = File(...)):
    db = SessionLocal()
    try:
        project = db.query(Project).filter(Project.id == project_id).first()
        if not project:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")

        results = []
        for upload in files:
            filename = upload.filename
            if not filename:
                continue

            content = _extract_file_text(upload, filename)
            document_type = filename.rsplit(".", 1)[-1].lower() if "." in filename else "unknown"
            document = Document(project_id=project_id, filename=filename, document_type=document_type, content=content)
            db.add(document)
            db.commit()
            db.refresh(document)
            index_document_chunks(db, document)
            _record_document_added(db, project_id, document)
            results.append({
                "id": document.id,
                "filename": document.filename,
                "document_type": document.document_type,
                "status": "uploaded",
            })

        return JSONResponse(status_code=201, content={"documents": results})
    finally:
        db.close()


@app.post("/documents")
def upload_document(
    project_id: int = Form(...),
    file: UploadFile = File(...),
    document_type: str | None = Form(None)
):
    filename = file.filename

    if not filename:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No filename")

    db = SessionLocal()
    try:
        project = db.query(Project).filter(Project.id == project_id).first()
        if not project:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")
    finally:
        db.close()

    content = _extract_file_text(file, filename)
    document_type_value = document_type or (filename.rsplit('.', 1)[-1].lower() if '.' in filename else 'unknown')

    db = SessionLocal()
    try:
        doc = Document(project_id=project_id, filename=filename, document_type=document_type_value, content=content)
        db.add(doc)
        db.commit()
        db.refresh(doc)
        # Keep both upload APIs equivalent: stored documents are immediately
        # searchable and eligible for analysis.
        index_document_chunks(db, doc)
        _record_document_added(db, project_id, doc)

        return JSONResponse(status_code=201, content={
            "id": doc.id,
            "filename": doc.filename,
            "document_type": doc.document_type,
            "status": "uploaded",
            "project_id": doc.project_id,
        })
    finally:
        db.close()


@app.get("/documents")
def list_documents(project_id: int | None = None):
    db = SessionLocal()
    try:
        query = db.query(Document)
        if project_id is not None:
            query = query.filter(Document.project_id == project_id)
        docs: List[Document] = query.order_by(desc(Document.uploaded_at)).all()

        results = []
        for d in docs:
            results.append({
                "id": d.id,
                "filename": d.filename,
                "document_type": d.document_type,
                "project_id": d.project_id,
                "status": "uploaded",
                "uploaded_at": d.uploaded_at.isoformat() if d.uploaded_at is not None else None,
            })

        return JSONResponse(status_code=200, content=results)
    finally:
        db.close()


@app.get("/projects/{project_id}/changes")
def list_project_changes(project_id: int):
    db = SessionLocal()
    try:
        changes = db.query(ChangeRecord).filter(ChangeRecord.project_id == project_id).order_by(ChangeRecord.created_at.desc()).all()
        return [{
            "id": change.id, "project_id": change.project_id, "subject": change.subject,
            "fact_type": change.fact_type, "old_value": change.old_value, "new_value": change.new_value,
            "source_document": change.source_document, "review_status": change.review_status,
            "timestamp": iso(change.created_at),
        } for change in changes]
    finally:
        db.close()


@app.post("/search")
def search_endpoint(body: dict = Body(...)):
    query = body.get("query")
    project_id = body.get("project_id")
    top_k = body.get("top_k", 5)
    if not query or not isinstance(query, str):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="query is required")
    if project_id is None or not isinstance(project_id, int):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="project_id is required")
    results = search(query, project_id=project_id, top_k=top_k)
    return JSONResponse(status_code=200, content={"results": results})


# Simple workflow stages
STAGES = [
    "LOAD_DOCUMENTS",
    "RETRIEVE_RELEVANT_CONTEXT",
    "EXTRACT_FACTS",
    "COMPARE_FACTS",
    "CREATE_DRAFT",
]


class WorkflowState(dict):
    pass


def _load_documents(state: WorkflowState, config: RunnableConfig | None = None) -> dict[str, Any]:
    if "LOAD_DOCUMENTS" in state.get("completed_stages", []):
        return {"document_ids": state.get("document_ids", [])}
    return {
        "document_ids": state.get("document_ids", []),
        "query": state.get("query", ""),
        "project_id": state.get("project_id"),
        "top_k": state.get("top_k", 5),
        "fallback_contexts": state.get("fallback_contexts", []),
    }


def _retrieve_relevant_context(state: WorkflowState, config: RunnableConfig | None = None) -> dict[str, Any]:
    if "RETRIEVE_RELEVANT_CONTEXT" in state.get("completed_stages", []):
        return {"retrieved_contexts": state.get("retrieved_contexts", [])}
    query = state.get("query", "")
    if not query or not isinstance(query, str):
        return {
            "retrieved_contexts": [],
            "document_ids": state.get("document_ids"),
            "query": query,
            "project_id": state.get("project_id"),
            "top_k": state.get("top_k", 5),
            "fallback_contexts": state.get("fallback_contexts", []),
        }
    document_ids = state.get("document_ids")
    project_id = state.get("project_id")
    return {
        "retrieved_contexts": retrieve_relevant_chunks(
            query,
            project_id=project_id,
            top_k=state.get("top_k", 5),
            document_ids=document_ids,
        ),
        "document_ids": document_ids,
        "query": query,
        "project_id": project_id,
        "top_k": state.get("top_k", 5),
        "fallback_contexts": state.get("fallback_contexts", []),
    }


def _extract_facts(state: WorkflowState, config: RunnableConfig | None = None) -> dict[str, Any]:
    if "EXTRACT_FACTS" in state.get("completed_stages", []):
        return {"extracted_facts": state.get("extracted_facts", [])}
    retrieved_contexts = list(state.get("retrieved_contexts", []) or [])
    fallback_contexts = state.get("fallback_contexts", [])
    if not retrieved_contexts:
        retrieved_contexts = fallback_contexts
    else:
        seen_ids = {ctx.get("document_id") for ctx in retrieved_contexts if ctx.get("document_id") is not None}
        for fallback in fallback_contexts:
            if fallback.get("document_id") not in seen_ids:
                retrieved_contexts.append(fallback)

    provider_result = extract_facts_from_contexts(retrieved_contexts, query=state.get("query"), include_metrics=True)
    llm_metrics = None
    if isinstance(provider_result, tuple):
        provider_facts, llm_metrics = provider_result
    else:
        provider_facts = provider_result
    deterministic_facts = extract_structured_milestone_facts(retrieved_contexts)
    existing = {(str(f.get("subject")).casefold(), f.get("fact_type"), str(f.get("normalized_value", f.get("value"))).casefold()) for f in deterministic_facts}
    provider_facts = deterministic_facts + [fact for fact in provider_facts if (str(fact.get("subject")).casefold(), fact.get("fact_type"), str(fact.get("normalized_value", fact.get("value"))).casefold()) not in existing]
    return {
        "extracted_facts": normalize_facts(provider_facts),
        "retrieved_contexts": retrieved_contexts,
        "document_ids": state.get("document_ids"),
        "query": state.get("query"),
        "project_id": state.get("project_id"),
        "top_k": state.get("top_k", 5),
        "fallback_contexts": fallback_contexts,
        "llm_metrics": llm_metrics,
    }


def _compare_facts(state: WorkflowState, config: RunnableConfig | None = None) -> dict[str, Any]:
    if "COMPARE_FACTS" in state.get("completed_stages", []):
        return {"conflicts": state.get("conflicts", [])}
    return {
        "conflicts": compare_facts(state.get("extracted_facts", [])),
        "extracted_facts": state.get("extracted_facts", []),
        "retrieved_contexts": state.get("retrieved_contexts", []),
        "document_ids": state.get("document_ids"),
        "query": state.get("query"),
        "project_id": state.get("project_id"),
        "top_k": state.get("top_k", 5),
        "fallback_contexts": state.get("fallback_contexts", []),
    }


def _route_after_compare_facts(state: WorkflowState, config: RunnableConfig | None = None) -> str:
    if any(c.get("status", "pending_review") == "pending_review" for c in state.get("conflicts", []) if isinstance(c, dict)):
        return graph.END
    return "create_draft"


def _create_draft(state: WorkflowState, config: RunnableConfig | None = None) -> dict[str, Any]:
    if "CREATE_DRAFT" in state.get("completed_stages", []):
        return {"draft": state.get("draft", {})}
    return {
        "draft": create_draft(state.get("extracted_facts", []), state.get("conflicts", [])),
        "conflicts": state.get("conflicts", []),
        "extracted_facts": state.get("extracted_facts", []),
        "retrieved_contexts": state.get("retrieved_contexts", []),
        "document_ids": state.get("document_ids"),
        "query": state.get("query"),
        "project_id": state.get("project_id"),
        "top_k": state.get("top_k", 5),
        "fallback_contexts": state.get("fallback_contexts", []),
    }


_STAGE_NODE_BY_STAGE = {
    "RETRIEVE_RELEVANT_CONTEXT": _retrieve_relevant_context,
    "EXTRACT_FACTS": _extract_facts,
    "COMPARE_FACTS": _compare_facts,
    "CREATE_DRAFT": _create_draft,
}

_STAGE_GRAPH_CACHE: dict[str, Any] = {}


def _get_stage_graph(stage_name: str) -> Any:
    if stage_name not in _STAGE_GRAPH_CACHE:
        builder = graph.StateGraph(dict)
        builder.add_node(stage_name, _wrap_stage_with_persistence(stage_name, _STAGE_NODE_BY_STAGE[stage_name]))
        builder.set_entry_point(stage_name)
        builder.set_finish_point(stage_name)
        _STAGE_GRAPH_CACHE[stage_name] = builder.compile()
    return _STAGE_GRAPH_CACHE[stage_name]


def _execute_stage_graph(stage_name: str, state: dict[str, Any]) -> dict[str, Any]:
    stage_graph = _get_stage_graph(stage_name)
    return stage_graph.invoke(state)


def _log_run(run_id: str, message: str) -> None:
    print(f"[RUN {run_id}] {message}")


def build_workflow_graph() -> Any:
    builder = graph.StateGraph(dict)
    builder.add_node("load_documents", _wrap_stage_with_persistence("LOAD_DOCUMENTS", _load_documents))
    builder.add_node("retrieve_relevant_context", _wrap_stage_with_persistence("RETRIEVE_RELEVANT_CONTEXT", _retrieve_relevant_context))
    builder.add_node("extract_facts", _wrap_stage_with_persistence("EXTRACT_FACTS", _extract_facts))
    builder.add_node("compare_facts", _wrap_stage_with_persistence("COMPARE_FACTS", _compare_facts))
    builder.add_node("create_draft", _wrap_stage_with_persistence("CREATE_DRAFT", _create_draft))
    builder.add_edge(graph.START, "load_documents")
    builder.add_edge("load_documents", "retrieve_relevant_context")
    builder.add_edge("retrieve_relevant_context", "extract_facts")
    builder.add_edge("extract_facts", "compare_facts")
    builder.add_conditional_edges("compare_facts", _route_after_compare_facts)
    builder.set_entry_point("load_documents")
    builder.set_finish_point("create_draft")
    return builder.compile()


# Compiled after persistence helpers are defined below.
WORKFLOW_GRAPH = None


def iso(dt):
    if dt is None:
        return None
    return dt.isoformat()


def _run_timing(run: Run) -> dict[str, Any]:
    end = run.updated_at if run.status in {"completed", "failed", "waiting_for_review"} else datetime.utcnow()
    duration_ms = int((end - run.created_at).total_seconds() * 1000) if run.created_at else None
    stages = _get_run_metadata(run.stages).get("stage_metrics", {})
    totals = _calculate_metric_totals(stages)
    return {
        "total_duration_ms": duration_ms,
        "total_input_tokens": totals["input_tokens"],
        "total_output_tokens": totals["output_tokens"],
        "total_tokens": totals["total_tokens"],
        "total_estimated_cost": totals["estimated_cost"],
        "stages": stages,
    }


def update_run(db, run: Run, **kwargs):
    for k, v in kwargs.items():
        setattr(run, k, v)
    run.updated_at = datetime.utcnow()
    db.add(run)
    db.commit()
    db.refresh(run)
    return run


def _get_run_metadata(stages: dict | None) -> dict[str, Any]:
    if not isinstance(stages, dict):
        return {}
    metadata = stages.get("_metadata")
    return metadata if isinstance(metadata, dict) else {}


def _merge_stages_with_metadata(stages: dict | None, metadata: dict[str, Any]) -> dict[str, Any]:
    merged = dict(stages or {})
    if metadata:
        merged["_metadata"] = metadata
    else:
        merged.pop("_metadata", None)
    return merged


def _strip_internal_stages(stages: dict | None) -> dict[str, Any]:
    if not isinstance(stages, dict):
        return {}
    return {k: v for k, v in stages.items() if k != "_metadata"}


def _calculate_metric_totals(stage_metrics: dict[str, Any] | None) -> dict[str, Any]:
    totals = {"input_tokens": None, "output_tokens": None, "total_tokens": None, "estimated_cost": None}
    if not isinstance(stage_metrics, dict):
        return totals

    input_sum = output_sum = total_sum = 0
    cost_sum = 0.0
    has_input = has_output = has_total = has_cost = False
    for metric in stage_metrics.values():
        if not isinstance(metric, dict):
            continue
        if isinstance(metric.get("input_tokens"), int):
            input_sum += metric["input_tokens"]
            has_input = True
        if isinstance(metric.get("output_tokens"), int):
            output_sum += metric["output_tokens"]
            has_output = True
        if isinstance(metric.get("total_tokens"), int):
            total_sum += metric["total_tokens"]
            has_total = True
        if isinstance(metric.get("estimated_cost"), (int, float)):
            cost_sum += float(metric["estimated_cost"])
            has_cost = True

    totals["input_tokens"] = input_sum if has_input else None
    totals["output_tokens"] = output_sum if has_output else None
    totals["total_tokens"] = total_sum if has_total else None
    totals["estimated_cost"] = round(cost_sum, 8) if has_cost else None
    return totals


def _build_stage_metric(
    started_at: datetime,
    completed_at: datetime,
    status: str,
    llm_metrics: dict[str, Any] | None = None,
    error: str | None = None,
) -> dict[str, Any]:
    llm_metrics = llm_metrics if isinstance(llm_metrics, dict) else {}
    duration_ms = int((completed_at - started_at).total_seconds() * 1000)
    if duration_ms <= 0:
        duration_ms = 1
    return {
        "started_at": started_at.isoformat(),
        "ended_at": completed_at.isoformat(),
        "duration_ms": duration_ms,
        "status": status,
        "model": llm_metrics.get("model"),
        "input_tokens": llm_metrics.get("input_tokens"),
        "output_tokens": llm_metrics.get("output_tokens"),
        "total_tokens": llm_metrics.get("total_tokens"),
        "estimated_cost": llm_metrics.get("estimated_cost"),
        "llm_duration_ms": llm_metrics.get("duration_ms"),
        "error": error or llm_metrics.get("error"),
    }


def _record_stage_metric(
    run_id: str,
    stage_name: str,
    started_at: datetime,
    completed_at: datetime,
    status: str,
    llm_metrics: dict[str, Any] | None = None,
    error: str | None = None,
) -> None:
    persisted = _update_run_stage_state(run_id, stage_name, status)
    if not persisted:
        return
    metadata = copy.deepcopy(_get_run_metadata(persisted.stages))
    metrics = dict(metadata.get("stage_metrics") or {})
    existing_metric = metrics.get(stage_name)
    if isinstance(existing_metric, dict) and existing_metric.get("status") == "completed":
        return
    metrics[stage_name] = _build_stage_metric(started_at, completed_at, status, llm_metrics, error)
    metadata["stage_metrics"] = metrics
    _update_run_stage_state(run_id, stage_name, status, stages=_merge_stages_with_metadata(persisted.stages, metadata))


_NODE_STAGE_MAP = {
    "load_documents": "LOAD_DOCUMENTS",
    "retrieve_relevant_context": "RETRIEVE_RELEVANT_CONTEXT",
    "extract_facts": "EXTRACT_FACTS",
    "compare_facts": "COMPARE_FACTS",
    "create_draft": "CREATE_DRAFT",
}


def _update_run_stage_state(run_id: str, stage_name: str, status: str, current_stage: str | None = None, **fields) -> Run | None:
    db = SessionLocal()
    try:
        run = db.query(Run).filter(Run.run_id == run_id).first()
        if run is None:
            return None

        stages = dict(run.stages or {})
        stages[stage_name] = status
        run.stages = _merge_stages_with_metadata(stages, _get_run_metadata(run.stages))
        run.current_stage = current_stage if current_stage is not None else stage_name
        for key, value in fields.items():
            setattr(run, key, value)
        run.updated_at = datetime.utcnow()
        db.add(run)
        db.commit()
        db.refresh(run)
        return run
    finally:
        db.close()


def _wrap_stage_with_persistence(stage_name: str, stage_fn):
    def wrapper(state: WorkflowState, config: RunnableConfig | None = None) -> dict[str, Any]:
        run_id = state.get("run_id")
        if stage_name in state.get("completed_stages", []):
            result = stage_fn(state, config)
            result["run_id"] = run_id
            return result

        if run_id:
            _log_run(run_id, f"{stage_name} START")
            _update_run_stage_state(run_id, stage_name, "in_progress", current_stage=stage_name)

        started_at = datetime.utcnow()
        try:
            result = stage_fn(state, config)
        except Exception as exc:
            completed_at = datetime.utcnow()
            llm_metrics = getattr(exc, "llm_metrics", None)
            if run_id:
                _log_run(run_id, f"{stage_name} ERROR {type(exc).__name__}: {exc}")
                _update_run_stage_state(run_id, stage_name, "failed", current_stage=stage_name, error=str(exc))
                _record_stage_metric(run_id, stage_name, started_at, completed_at, "error", llm_metrics, str(exc))
            raise
        result["run_id"] = run_id
        if run_id:
            outputs: dict[str, Any] = {}
            if stage_name == "RETRIEVE_RELEVANT_CONTEXT":
                outputs["retrieved_contexts"] = result.get("retrieved_contexts", [])
            elif stage_name == "EXTRACT_FACTS":
                outputs["extracted_facts"] = result.get("extracted_facts", [])
            elif stage_name == "COMPARE_FACTS":
                outputs["conflicts"] = result.get("conflicts", [])
            elif stage_name == "CREATE_DRAFT":
                outputs["draft"] = result.get("draft", {})

            completed_at = datetime.utcnow()
            persisted = _update_run_stage_state(run_id, stage_name, "completed", **outputs)
            if persisted:
                metadata = copy.deepcopy(_get_run_metadata(persisted.stages))
                metrics = dict(metadata.get("stage_metrics") or {})
                existing_metric = metrics.get(stage_name)
                if not (isinstance(existing_metric, dict) and existing_metric.get("status") == "completed"):
                    metrics[stage_name] = _build_stage_metric(
                        started_at,
                        completed_at,
                        "completed",
                        result.get("llm_metrics"),
                    )
                    metadata["stage_metrics"] = metrics
                    _update_run_stage_state(run_id, stage_name, "completed", **{"stages": _merge_stages_with_metadata(persisted.stages, metadata)})
            _log_run(run_id, f"{stage_name} END completed")

        return result

    return wrapper


def _get_examine_state(run: Run) -> dict[str, Any]:
    metadata = _get_run_metadata(run.stages)
    examine = metadata.get("examine")
    return examine if isinstance(examine, dict) else {}


def _save_examine_state(db, run: Run, examine_state: dict[str, Any]) -> Run:
    # JSON columns require a fresh nested value; mutating the object loaded
    # from SQLAlchemy can otherwise be invisible to change tracking.
    metadata = copy.deepcopy(_get_run_metadata(run.stages))
    metadata["examine"] = copy.deepcopy(examine_state)
    run.stages = _merge_stages_with_metadata(copy.deepcopy(run.stages), metadata)
    run.updated_at = datetime.utcnow()
    db.add(run)
    db.commit()
    db.refresh(run)
    return run


def _save_examine_metric(db, run: Run, llm_metrics: dict[str, Any] | None) -> Run:
    if not isinstance(llm_metrics, dict):
        return run
    ended_at = datetime.utcnow()
    duration_ms = llm_metrics.get("duration_ms") if isinstance(llm_metrics.get("duration_ms"), int) and llm_metrics.get("duration_ms") > 0 else 1
    started_at = ended_at - timedelta(milliseconds=duration_ms)
    metadata = copy.deepcopy(_get_run_metadata(run.stages))
    metrics = dict(metadata.get("stage_metrics") or {})
    metrics["EXAMINE"] = _build_stage_metric(
        started_at,
        ended_at,
        llm_metrics.get("status") or "completed",
        llm_metrics,
        llm_metrics.get("error"),
    )
    metadata["stage_metrics"] = metrics
    run.stages = _merge_stages_with_metadata(copy.deepcopy(run.stages), metadata)
    run.updated_at = datetime.utcnow()
    db.add(run)
    db.commit()
    db.refresh(run)
    return run


def _first_non_completed_stage(stages: dict | None) -> str | None:
    for stage in STAGES:
        if (stages or {}).get(stage) != "completed":
            return stage
    return None


def _build_recovery_state(run: Run, db) -> dict[str, Any]:
    metadata = _get_run_metadata(run.stages)
    document_ids = metadata.get("document_ids") or []
    query = metadata.get("query", "")
    top_k = metadata.get("top_k", 5)

    fallback_contexts: list[dict[str, Any]] = []
    if document_ids and run.project_id is not None:
        docs = (
            db.query(Document)
            .filter(Document.id.in_(document_ids), Document.project_id == run.project_id)
            .all()
        )
        fallback_contexts = [
            {
                "source_filename": d.filename,
                "document_id": d.id,
                "chunk_index": 0,
                "text": d.content or "",
            }
            for d in docs
            if d.content
        ]

    return {
        "document_ids": document_ids,
        "query": query,
        "project_id": run.project_id,
        "top_k": top_k,
        "fallback_contexts": fallback_contexts,
    }


def _resume_run_if_needed(run: Run, db) -> Run:
    if run.status != "running" or run.current_stage == "WAITING_FOR_REVIEW" or run.current_stage == "COMPLETED":
        return run

    stages = run.stages or {}
    metadata = _get_run_metadata(stages)
    if not metadata:
        return run

    next_stage = _first_non_completed_stage(stages)
    if next_stage is None:
        # If all workflow stages are marked completed but the run is still running,
        # finalize the run only if it already has a draft or no conflicts remain.
        if run.draft is not None or not (run.conflicts or []):
            run = update_run(
                db,
                run,
                status="completed",
                current_stage="COMPLETED",
                stages=_merge_stages_with_metadata({s: "completed" for s in STAGES}, _get_run_metadata(run.stages)),
            )
        return run

    for stage in STAGES:
        if stage == next_stage:
            break
        if (stages or {}).get(stage) == "completed":
            _log_run(run.run_id, f"skipping completed {stage}")

    _log_run(run.run_id, f"resuming from {next_stage}")
    recovery_state = _build_recovery_state(run, db)

    try:
        # Recovery uses the same compiled production graph as POST /runs.  Nodes
        # receive persisted outputs and skip only stages already completed, so an
        # interrupted run does not repeat retrieval or provider work.
        completed_stages = [stage for stage in STAGES if (stages or {}).get(stage) == "completed"]
        result = WORKFLOW_GRAPH.invoke({
            **recovery_state,
            "run_id": run.run_id,
            "retrieved_contexts": run.retrieved_contexts or [],
            "extracted_facts": run.extracted_facts or [],
            "conflicts": run.conflicts or [],
            "draft": run.draft or {},
            "completed_stages": completed_stages,
        })
        conflicts = result.get("conflicts", []) or []
        if conflicts:
            return update_run(
                db, run, status="waiting_for_review", current_stage="WAITING_FOR_REVIEW",
                stages=_merge_stages_with_metadata({
                    "LOAD_DOCUMENTS": "completed", "RETRIEVE_RELEVANT_CONTEXT": "completed",
                    "EXTRACT_FACTS": "completed", "COMPARE_FACTS": "completed",
                    "WAITING_FOR_REVIEW": "in_progress",
                }, _get_run_metadata(run.stages)), conflicts=conflicts, draft=None,
            )
        return update_run(
            db, run, status="completed", current_stage="COMPLETED",
            stages=_merge_stages_with_metadata({stage: "completed" for stage in STAGES}, _get_run_metadata(run.stages)),
            conflicts=[], draft=result.get("draft", {}),
        )

        # Kept below for migration readability; this return makes recovery use
        # the compiled graph above rather than manually executing stage graphs.
        if next_stage == "LOAD_DOCUMENTS":
            document_ids = recovery_state.get("document_ids") or []
            if not document_ids:
                return run
            existing_docs = (
                db.query(Document)
                .filter(Document.id.in_(document_ids), Document.project_id == run.project_id)
                .all()
            )
            if len(existing_docs) != len(set(document_ids)):
                run = update_run(db, run, status="failed", current_stage="LOAD_DOCUMENTS", error="Missing or invalid document ids during resume")
                return run
            stages = _merge_stages_with_metadata({"LOAD_DOCUMENTS": "completed", "RETRIEVE_RELEVANT_CONTEXT": "in_progress"}, metadata)
            run = update_run(db, run, current_stage="RETRIEVE_RELEVANT_CONTEXT", stages=stages)
            next_stage = "RETRIEVE_RELEVANT_CONTEXT"

        if next_stage == "RETRIEVE_RELEVANT_CONTEXT":
            _log_run(run.run_id, "executing RETRIEVE_RELEVANT_CONTEXT")
            run = update_run(
                db,
                run,
                current_stage="RETRIEVE_RELEVANT_CONTEXT",
                stages=_merge_stages_with_metadata({
                    "LOAD_DOCUMENTS": "completed",
                    "RETRIEVE_RELEVANT_CONTEXT": "in_progress",
                }, metadata),
            )
            state = {**recovery_state}
            retrieved = _execute_stage_graph("RETRIEVE_RELEVANT_CONTEXT", state)
            retrieved_contexts = retrieved.get("retrieved_contexts", [])
            stages = _merge_stages_with_metadata({
                "LOAD_DOCUMENTS": "completed",
                "RETRIEVE_RELEVANT_CONTEXT": "completed",
                "EXTRACT_FACTS": "in_progress",
            }, metadata)
            run = update_run(
                db,
                run,
                current_stage="EXTRACT_FACTS",
                stages=stages,
                retrieved_contexts=retrieved_contexts,
            )
            _log_run(run.run_id, "completed RETRIEVE_RELEVANT_CONTEXT")
            next_stage = "EXTRACT_FACTS"

        if next_stage == "EXTRACT_FACTS":
            _log_run(run.run_id, "executing EXTRACT_FACTS")
            run = update_run(
                db,
                run,
                current_stage="EXTRACT_FACTS",
                stages=_merge_stages_with_metadata({
                    "LOAD_DOCUMENTS": "completed",
                    "RETRIEVE_RELEVANT_CONTEXT": "completed",
                    "EXTRACT_FACTS": "in_progress",
                }, metadata),
            )
            state = {
                "retrieved_contexts": run.retrieved_contexts or [],
                "query": recovery_state.get("query", ""),
                "project_id": run.project_id,
                "top_k": recovery_state.get("top_k", 5),
                "fallback_contexts": recovery_state.get("fallback_contexts", []),
            }
            extracted = _execute_stage_graph("EXTRACT_FACTS", state)
            extracted_facts = extracted.get("extracted_facts", [])
            stages = _merge_stages_with_metadata({
                "LOAD_DOCUMENTS": "completed",
                "RETRIEVE_RELEVANT_CONTEXT": "completed",
                "EXTRACT_FACTS": "completed",
                "COMPARE_FACTS": "in_progress",
            }, metadata)
            run = update_run(
                db,
                run,
                current_stage="COMPARE_FACTS",
                stages=stages,
                extracted_facts=extracted_facts,
            )
            _log_run(run.run_id, "completed EXTRACT_FACTS")
            next_stage = "COMPARE_FACTS"

        if next_stage == "COMPARE_FACTS":
            _log_run(run.run_id, "executing COMPARE_FACTS")
            run = update_run(
                db,
                run,
                current_stage="COMPARE_FACTS",
                stages=_merge_stages_with_metadata({
                    "LOAD_DOCUMENTS": "completed",
                    "RETRIEVE_RELEVANT_CONTEXT": "completed",
                    "EXTRACT_FACTS": "completed",
                    "COMPARE_FACTS": "in_progress",
                }, metadata),
            )
            state = {
                "extracted_facts": run.extracted_facts or [],
                "retrieved_contexts": run.retrieved_contexts or [],
                "document_ids": recovery_state.get("document_ids", []),
                "query": recovery_state.get("query", ""),
                "project_id": run.project_id,
                "top_k": recovery_state.get("top_k", 5),
                "fallback_contexts": recovery_state.get("fallback_contexts", []),
            }
            compared = _execute_stage_graph("COMPARE_FACTS", state)
            conflicts = compared.get("conflicts", [])
            if conflicts:
                stages = _merge_stages_with_metadata({
                    "LOAD_DOCUMENTS": "completed",
                    "RETRIEVE_RELEVANT_CONTEXT": "completed",
                    "EXTRACT_FACTS": "completed",
                    "COMPARE_FACTS": "completed",
                    "WAITING_FOR_REVIEW": "in_progress",
                }, metadata)
                run = update_run(
                    db,
                    run,
                    status="waiting_for_review",
                    current_stage="WAITING_FOR_REVIEW",
                    stages=stages,
                    conflicts=conflicts,
                )
                _log_run(run.run_id, "completed COMPARE_FACTS, waiting for review")
                return run
            run = update_run(
                db,
                run,
                current_stage="CREATE_DRAFT",
                stages=_merge_stages_with_metadata({
                    "LOAD_DOCUMENTS": "completed",
                    "RETRIEVE_RELEVANT_CONTEXT": "completed",
                    "EXTRACT_FACTS": "completed",
                    "COMPARE_FACTS": "completed",
                    "CREATE_DRAFT": "in_progress",
                }, metadata),
                conflicts=conflicts,
            )
            _log_run(run.run_id, "completed COMPARE_FACTS")
            next_stage = "CREATE_DRAFT"

        if next_stage == "CREATE_DRAFT":
            _log_run(run.run_id, "executing CREATE_DRAFT")
            run = update_run(
                db,
                run,
                current_stage="CREATE_DRAFT",
                stages=_merge_stages_with_metadata({
                    "LOAD_DOCUMENTS": "completed",
                    "RETRIEVE_RELEVANT_CONTEXT": "completed",
                    "EXTRACT_FACTS": "completed",
                    "COMPARE_FACTS": "completed",
                    "CREATE_DRAFT": "in_progress",
                }, metadata),
            )
            state = {
                "extracted_facts": run.extracted_facts or [],
                "conflicts": run.conflicts or [],
                "retrieved_contexts": run.retrieved_contexts or [],
                "document_ids": recovery_state.get("document_ids", []),
                "query": recovery_state.get("query", ""),
                "project_id": run.project_id,
                "top_k": recovery_state.get("top_k", 5),
                "fallback_contexts": recovery_state.get("fallback_contexts", []),
            }
            draft_state = _execute_stage_graph("CREATE_DRAFT", state)
            draft = draft_state.get("draft", {})
            run = update_run(
                db,
                run,
                status="completed",
                current_stage="COMPLETED",
                stages={s: "completed" for s in STAGES},
                draft=draft,
            )
            _log_run(run.run_id, "completed CREATE_DRAFT")

    except Exception as exc:
        traceback.print_exc()
        run = update_run(db, run, status="failed", current_stage=next_stage, error=str(exc))

    return run


def _all_conflicts_reviewed(conflicts: list[dict[str, Any]]) -> bool:
    terminal_decisions = {"accept_a", "accept_b", "reject_conflict"}
    for conflict in conflicts or []:
        if conflict.get("status") == "pending_review" or conflict.get("decision") not in terminal_decisions:
            return False
    return True


def _extract_fact_comparison_key(fact: dict[str, Any]) -> tuple[str | None, str | None, str | None]:
    value = fact.get("normalized_value", fact.get("value"))
    source = fact.get("source_document") or fact.get("filename")
    evidence = fact.get("evidence")
    return (str(value).strip() if value is not None else None,
            str(source).strip() if source is not None else None,
            str(evidence).strip() if evidence is not None else None)


def _apply_conflict_reviews_to_facts(extracted_facts: list[dict[str, Any]], conflicts: list[dict[str, Any]]) -> list[dict[str, Any]]:
    if not extracted_facts:
        return []

    removals: set[tuple[str | None, str | None, str | None]] = set()
    for conflict in conflicts or []:
        status = conflict.get("status")
        if status not in ("resolved", "rejected"):
            continue

        a_key = (str(conflict.get("fact_a")).strip() if conflict.get("fact_a") is not None else None,
                 str(conflict.get("source_a")).strip() if conflict.get("source_a") is not None else None,
                 str(conflict.get("evidence_a")).strip() if conflict.get("evidence_a") is not None else None)
        b_key = (str(conflict.get("fact_b")).strip() if conflict.get("fact_b") is not None else None,
                 str(conflict.get("source_b")).strip() if conflict.get("source_b") is not None else None,
                 str(conflict.get("evidence_b")).strip() if conflict.get("evidence_b") is not None else None)

        if conflict.get("decision") == "accept_a":
            removals.add(b_key)
        elif conflict.get("decision") == "accept_b":
            removals.add(a_key)
        elif conflict.get("decision") == "reject_conflict":
            removals.add(a_key)
            removals.add(b_key)

    result: list[dict[str, Any]] = []
    for fact in extracted_facts:
        fact_key = _extract_fact_comparison_key(fact)
        if fact_key in removals:
            continue
        result.append(fact)

    return result


WORKFLOW_GRAPH = build_workflow_graph()


def extract_facts_from_text(doc):
    text = doc.content or ""
    facts = []

    # simple date pattern e.g., August 20, 2026 or Aug 20 2026
    month = r"(?:Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|Jul(?:y)?|Aug(?:ust)?|Sep(?:t(?:ember)?)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?)"
    date_re = re.compile(rf"({month} \d{{1,2}},? \d{{4}})", re.IGNORECASE)

    def parse_date_to_iso(s: str):
        if not s:
            return None
        s = s.replace(',', '').strip()
        for fmt in ('%B %d %Y', '%b %d %Y'):
            try:
                dt = datetime.strptime(s, fmt)
                return dt.date().isoformat()
            except Exception:
                continue
        return s

    # owners: lines like Owner: Name
    for m in re.finditer(r"Owner:\s*(.+)", text, re.IGNORECASE):
        evidence = m.group(0).strip()
        facts.append({
            "document_id": doc.id,
            "filename": doc.filename,
            "category": "owners",
            "fact": m.group(1).strip(),
            "evidence": evidence,
        })

    # milestones with dates: process per-line to avoid cross-line association
    for line in text.splitlines():
        lm = re.search(rf"^\s*(?:\d+\.\s*)?(?P<subject>[^—\-:]+?)\s*(?:—|-|:).*?(?:due|due date:|due:|moved to)\s+{date_re.pattern}", line, re.IGNORECASE)
        if lm:
            milestone = lm.group('subject').strip()
            dm = date_re.search(lm.group(0))
            date_str = dm.group(1).strip() if dm else None
            iso_date = parse_date_to_iso(date_str) if date_str else None
            facts.append({
                "document_id": doc.id,
                "filename": doc.filename,
                "category": "milestones",
                "fact": {"subject": milestone, "attribute": "due_date", "value": iso_date},
                "evidence": line.strip(),
            })

    # subject line followed by owner/due metadata on subsequent lines
    lines = text.splitlines()
    for index, line in enumerate(lines):
        subject_line = line.strip()
        if not subject_line or re.search(r"\b(?:Owner|Due|Due date|milestone)\b", subject_line, re.IGNORECASE):
            continue
        next_lines = " ".join(lines[index + 1 : index + 3])
        if not re.search(r"Owner:\s*.+", next_lines, re.IGNORECASE):
            continue
        due_match = re.search(rf"Due:?\s*{date_re.pattern}", next_lines, re.IGNORECASE)
        if not due_match:
            continue
        date_str = due_match.group(1).strip()
        iso_date = parse_date_to_iso(date_str) if date_str else None
        facts.append({
            "document_id": doc.id,
            "filename": doc.filename,
            "category": "milestones",
            "fact": {"subject": subject_line, "attribute": "due_date", "value": iso_date},
            "evidence": f"{subject_line} / {next_lines.strip()}",
        })

    # detect generic milestone movement statements such as
    # "The Payment Integration milestone was moved from September 25 to September 28, 2026."
    moved_re = re.compile(
        rf"(?:The\s+)?(?P<subject>.+?)\s+milestone.*?moved(?:\s+from\s+{date_re.pattern})?\s+to\s+(?P<new_date>{date_re.pattern})",
        re.IGNORECASE,
    )
    for m in moved_re.finditer(text):
        milestone = m.group("subject").strip()
        date_str = m.group("new_date").strip()
        iso_date = parse_date_to_iso(date_str) if date_str else None
        facts.append({
            "document_id": doc.id,
            "filename": doc.filename,
            "category": "milestones",
            "fact": {"subject": milestone, "attribute": "due_date", "value": iso_date},
            "evidence": m.group(0).strip(),
        })

    # generic owner statements such as "David remains responsible." or "Alice is responsible."
    for m in re.finditer(r"([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)\s+(?:remains|is)\s+(?:responsible|accountable)", text):
        facts.append({
            "document_id": doc.id,
            "filename": doc.filename,
            "category": "owners",
            "fact": m.group(1).strip(),
            "evidence": m.group(0).strip(),
        })

    # generic date mentions (for other categories)
    for m in date_re.finditer(text):
        evidence = m.group(0).strip()
        facts.append({
            "document_id": doc.id,
            "filename": doc.filename,
            "category": "dates",
            "fact": evidence,
            "evidence": evidence,
        })

    # risks: capture lines under RISKS heading or lines containing 'risk'
    if "RISKS" in text.upper():
        parts = re.split(r"RISKS", text, flags=re.IGNORECASE)
        if len(parts) > 1:
            after = parts[1]
            # take first 5 lines as risks block
            lines = after.strip().splitlines()
            for i, line in enumerate(lines[:10]):
                if line.strip():
                    facts.append({
                        "document_id": doc.id,
                        "filename": doc.filename,
                        "category": "risks",
                        "fact": line.strip(),
                        "evidence": line.strip(),
                    })

    # decisions and action items: look for keywords
    for m in re.finditer(r"Decision:\s*(.+)", text, re.IGNORECASE):
        facts.append({
            "document_id": doc.id,
            "filename": doc.filename,
            "category": "decisions",
            "fact": m.group(1).strip(),
            "evidence": m.group(0).strip(),
        })

    for m in re.finditer(r"Action(?: item)?:\s*(.+)", text, re.IGNORECASE):
        facts.append({
            "document_id": doc.id,
            "filename": doc.filename,
            "category": "action_items",
            "fact": m.group(1).strip(),
            "evidence": m.group(0).strip(),
        })

    return facts


@app.post("/runs")
def create_run(body: dict = Body(...)):
    if not isinstance(body, dict):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Request body must be an object")

    project_id = body.get("project_id")
    document_ids = body.get("document_ids")
    query = body.get("query")
    top_k = body.get("top_k", 5)
    base_run_id = body.get("base_run_id")

    if project_id is None or not isinstance(project_id, int):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="project_id is required")
    if not document_ids or not isinstance(document_ids, list):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="document_ids is required")

    db = SessionLocal()
    try:
        project = db.query(Project).filter(Project.id == project_id).first()
        if not project:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")

        existing_docs = (
            db.query(Document)
            .filter(Document.id.in_(document_ids), Document.project_id == project_id)
            .all()
        )
        if len(existing_docs) != len(set(document_ids)):
            existing_ids = {d.id for d in existing_docs}
            missing = [str(did) for did in document_ids if did not in existing_ids]
            run = Run(
                status="failed",
                project_id=project_id,
                current_stage="LOAD_DOCUMENTS",
                stages=_merge_stages_with_metadata({"LOAD_DOCUMENTS": "failed"}, {
                    "document_ids": document_ids,
                    "query": query,
                    "top_k": top_k,
                }),
                error=f"Missing or invalid document ids {missing}",
            )
            db.add(run)
            db.commit()
            db.refresh(run)
            return JSONResponse(status_code=400, content={"error": f"Missing or invalid document ids {missing}"})

        retrieval_query = (
            query.strip()
            if query and isinstance(query, str) and query.strip()
            else "Extract meaningful project facts from the supplied evidence."
        )
        metadata = {
            "document_ids": document_ids,
            "query": retrieval_query,
            "top_k": top_k,
        }

        if base_run_id is not None:
            if not isinstance(base_run_id, str) or not base_run_id.strip():
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="base_run_id must be a string")
            base_run = db.query(Run).filter(Run.run_id == base_run_id, Run.project_id == project_id).first()
            if not base_run:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Base run not found")
            if base_run.status != "completed":
                raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Base run must be completed before incremental update")
            if base_run.conflicts and not _all_conflicts_reviewed(base_run.conflicts):
                raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Base run must be fully reviewed before incremental update")
            base_document_ids = set(_get_run_metadata(base_run.stages).get("document_ids") or [])
            incremental_document_ids = [doc_id for doc_id in document_ids if doc_id not in base_document_ids]
            if not incremental_document_ids:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Incremental update requires at least one new document")
            document_ids = incremental_document_ids
            metadata["document_ids"] = document_ids
            metadata["base_run_id"] = base_run_id
            metadata["incremental_document_ids"] = document_ids
            metadata["mode"] = "incremental"
        else:
            base_run = None

        run = Run(
            status="running",
            project_id=project_id,
            current_stage="LOAD_DOCUMENTS",
            stages=_merge_stages_with_metadata({"LOAD_DOCUMENTS": "in_progress"}, metadata),
        )
        db.add(run)
        db.commit()
        db.refresh(run)

        analysis_docs = [d for d in existing_docs if d.id in document_ids]
        fallback_contexts = [
            {
                "source_filename": d.filename,
                "document_id": d.id,
                "chunk_index": 0,
                "text": d.content or "",
            }
            for d in analysis_docs
            if d.content
        ]

        workflow_state = {
            "run_id": run.run_id,
            "document_ids": document_ids,
            "query": retrieval_query,
            "project_id": project_id,
            "top_k": top_k,
            "fallback_contexts": fallback_contexts,
        }

        try:
            if base_run is not None:
                _log_run(run.run_id, f"executing incremental update from {base_run_id}")
                load_started = datetime.utcnow()
                _record_stage_metric(run.run_id, "LOAD_DOCUMENTS", load_started, datetime.utcnow(), "completed")
                retrieved = _execute_stage_graph("RETRIEVE_RELEVANT_CONTEXT", workflow_state)
                retrieved_contexts = retrieved.get("retrieved_contexts", [])
                extracted = _execute_stage_graph(
                    "EXTRACT_FACTS",
                    {
                        "run_id": run.run_id,
                        "retrieved_contexts": retrieved_contexts,
                        "query": retrieval_query,
                        "project_id": project_id,
                        "document_ids": document_ids,
                        "top_k": top_k,
                        "fallback_contexts": fallback_contexts,
                    },
                )
                new_facts = extracted.get("extracted_facts", [])
                base_facts = base_run.extracted_facts or []
                compare_started = datetime.utcnow()
                affected_base_facts = select_affected_base_facts(base_facts, new_facts)
                merged_facts, conflicts, _ = merge_incremental_facts(base_facts, new_facts)
                record_incremental_fact_changes(db, project_id, affected_base_facts, new_facts)
                _record_stage_metric(run.run_id, "COMPARE_FACTS", compare_started, datetime.utcnow(), "completed")
                db.refresh(run)

                if conflicts:
                    run = update_run(
                        db,
                        run,
                        status="waiting_for_review",
                        current_stage="WAITING_FOR_REVIEW",
                        stages=_merge_stages_with_metadata({
                            "LOAD_DOCUMENTS": "completed",
                            "RETRIEVE_RELEVANT_CONTEXT": "completed",
                            "EXTRACT_FACTS": "completed",
                            "COMPARE_FACTS": "completed",
                            "WAITING_FOR_REVIEW": "in_progress",
                        }, _get_run_metadata(run.stages)),
                        retrieved_contexts=retrieved_contexts,
                        extracted_facts=merged_facts,
                        conflicts=conflicts,
                        draft=None,
                    )
                    _log_run(run.run_id, "incremental update completed with conflicts, waiting for review")
                    return JSONResponse(status_code=201, content={"run_id": run.run_id})

                draft_started = datetime.utcnow()
                draft = build_incremental_draft(base_run.draft, merged_facts, [], new_facts)
                _record_stage_metric(run.run_id, "CREATE_DRAFT", draft_started, datetime.utcnow(), "completed")
                db.refresh(run)
                run = update_run(
                    db,
                    run,
                    status="completed",
                    current_stage="COMPLETED",
                    stages=_merge_stages_with_metadata({s: "completed" for s in STAGES}, _get_run_metadata(run.stages)),
                    retrieved_contexts=retrieved_contexts,
                    extracted_facts=merged_facts,
                    conflicts=[],
                    draft=draft,
                )
                _log_run(run.run_id, "incremental update completed successfully")
                return JSONResponse(status_code=201, content={"run_id": run.run_id})

            _log_run(run.run_id, "executing workflow graph")
            result = WORKFLOW_GRAPH.invoke(workflow_state)
            db.refresh(run)

            conflicts = result.get("conflicts", []) or []
            if conflicts:
                run = update_run(
                    db,
                    run,
                    status="waiting_for_review",
                    current_stage="WAITING_FOR_REVIEW",
                    stages=_merge_stages_with_metadata({
                        "LOAD_DOCUMENTS": "completed",
                        "RETRIEVE_RELEVANT_CONTEXT": "completed",
                        "EXTRACT_FACTS": "completed",
                        "COMPARE_FACTS": "completed",
                        "WAITING_FOR_REVIEW": "in_progress",
                    }, _get_run_metadata(run.stages)),
                    conflicts=conflicts,
                    draft=None,
                )
                _log_run(run.run_id, "workflow completed with conflicts, waiting for review")
                return JSONResponse(status_code=201, content={"run_id": run.run_id})

            draft = result.get("draft", {})
            previous = (
                db.query(Run).filter(Run.project_id == project_id, Run.status == "completed", Run.run_id != run.run_id)
                .order_by(Run.updated_at.desc()).first()
            )
            _record_fact_changes(db, project_id, previous.extracted_facts if previous else [], result.get("extracted_facts", []))
            run = update_run(
                db,
                run,
                status="completed",
                current_stage="COMPLETED",
                stages=_merge_stages_with_metadata({s: "completed" for s in STAGES}, _get_run_metadata(run.stages)),
                conflicts=[],
                draft=draft,
            )
            _log_run(run.run_id, "workflow completed successfully")
            return JSONResponse(status_code=201, content={"run_id": run.run_id})
        except Exception as e:
            print(f"RUNS ERROR [WORKFLOW]: {type(e).__name__}: {e}")
            traceback.print_exc()
            db.refresh(run)
            failed_stage = run.current_stage or "LOAD_DOCUMENTS"
            failed_stages = dict(run.stages or {})
            failed_stages[failed_stage] = "failed"
            run = update_run(db, run, status="failed", current_stage=failed_stage, stages=failed_stages, error=str(e))
            return JSONResponse(status_code=500, content={"error": str(e)})
    finally:
        db.close()


@app.get("/runs/{run_id}")
def get_run(run_id: str):
    db = SessionLocal()
    try:
        run = db.query(Run).filter(Run.run_id == run_id).first()
        if not run:
            return JSONResponse(status_code=404, content={"error": "run not found"})

        if run.status == "running":
            run = _resume_run_if_needed(run, db)

        return JSONResponse(status_code=200, content={
            "run_id": run.run_id,
            "status": run.status,
            "current_stage": run.current_stage,
            "stages": _strip_internal_stages(run.stages),
            "metadata": _get_run_metadata(run.stages),
            "retrieved_contexts": run.retrieved_contexts,
            "extracted_facts": run.extracted_facts,
            "conflicts": run.conflicts,
            "draft": run.draft,
            "error": run.error,
            "timing": _run_timing(run),
            "created_at": iso(run.created_at),
            "updated_at": iso(run.updated_at),
        })
    finally:
        db.close()



@app.get("/runs/{run_id}/report")
def get_run_report(run_id: str):
    db = SessionLocal()
    try:
        run = db.query(Run).filter(Run.run_id == run_id).first()
        if not run:
            return JSONResponse(status_code=404, content={"error": "run not found"})

        if run.status != "completed":
            return JSONResponse(status_code=409, content={"error": "report is only available for completed runs"})

        extracted = run.extracted_facts or []
        conflicts = run.conflicts or []
        draft = run.draft or {}

        # helper: find milestone facts by subject -> list of facts
        milestones_by_subject = {}
        for f in extracted:
            if f.get("category") == "milestone":
                subj = f.get("subject")
                if not subj:
                    fact = f.get("fact")
                    if isinstance(fact, dict):
                        subj = fact.get("subject")
                if subj:
                    milestones_by_subject.setdefault(subj.strip().lower(), []).append(f)

        # map conflicts by subject+attribute
        conflicts_by_subject = {}
        for c in conflicts:
            # use description to extract subject if possible, else conflict_id
            subj = None
            # try to find subject in description like "Conflicting due_date for subject 'api integration'"
            m = re.search(r"subject '\s*([^']+?)\s*'", (c.get("description") or ""), re.IGNORECASE)
            if m:
                subj = m.group(1).strip().lower()
            else:
                # fallback to source info
                subj = None
            if subj:
                conflicts_by_subject.setdefault(subj, []).append(c)

        # Build milestones list for report
        report_milestones = []
        for subj_key, facts in milestones_by_subject.items():
            # canonical subject display (take first's subject)
            first = facts[0]
            subject_display = first.get("subject") or subj_key

            # Default values
            chosen_due = None
            chosen_owner = None
            chosen_source = None
            chosen_evidence = None
            human_reviewed = False

            # If there's a reviewed conflict for this subject, prefer accepted fact
            subj_conflicts = conflicts_by_subject.get(subj_key, [])
            chosen_conflict = None
            for cc in subj_conflicts:
                if cc.get("status") == "resolved" and cc.get("decision") in ("accept_a", "accept_b"):
                    chosen_conflict = cc
                    break

            if chosen_conflict:
                # use accepted_fact and choose source/evidence according to decision
                chosen_due = chosen_conflict.get("accepted_fact")
                human_reviewed = True
                # pick evidence/source from accepted side
                if chosen_conflict.get("decision") == "accept_a":
                    chosen_source = chosen_conflict.get("source_a")
                    chosen_evidence = chosen_conflict.get("evidence_a")
                else:
                    chosen_source = chosen_conflict.get("source_b")
                    chosen_evidence = chosen_conflict.get("evidence_b")

            # If no human-reviewed override, choose the due_date milestone value
            if not chosen_due:
                for f in facts:
                    if f.get("fact_type") == "due_date" and f.get("value"):
                        chosen_due = f.get("value")
                        chosen_source = f.get("source_document") or f.get("filename")
                        chosen_evidence = f.get("evidence")
                        break

            # owner: attempt to parse from the milestone evidence (owner: Name)
            owner_found = None
            owner_re = re.compile(r"owner[:\s]*([^—,\n]+)", re.IGNORECASE)
            for f in facts:
                ev = f.get("evidence") or ""
                m = owner_re.search(ev)
                if m:
                    owner_found = m.group(1).strip()
                    break

            # If no owner found in evidence, look in owners extracted facts for matching subject
            if not owner_found:
                for o in extracted:
                    if o.get("category") == "owners":
                        ev = o.get("evidence") or ""
                        # if subject appears in evidence or filename matches, consider matching
                        if subject_display and subject_display.lower() in (o.get("fact") or "").lower():
                            owner_found = o.get("fact")
                            break

            chosen_owner = owner_found

            report_milestones.append({
                "subject": subject_display,
                "due_date": chosen_due,
                "owner": chosen_owner,
                "status": None,
                "source_document": chosen_source,
                "evidence": chosen_evidence,
                "human_reviewed": human_reviewed,
            })

        # Draft creation canonicalizes attributes under one logical subject. It
        # is the report's preferred representation; the legacy reconstruction
        # above remains as a backwards-compatible fallback for old runs.
        if isinstance(draft.get("milestones"), list):
            report_milestones = [
                {
                    "subject": item.get("subject"),
                    "due_date": item.get("due_date"),
                    "owner": item.get("owner"),
                    "status": item.get("status"),
                    "source_document": item.get("source_document"),
                    "evidence": item.get("evidence"),
                    "human_reviewed": False,
                }
                for item in draft["milestones"] if isinstance(item, dict)
            ]

        # Owners list
        report_owners = []
        for o in extracted:
            if o.get("category") == "owners":
                report_owners.append({
                    "subject": None,
                    "owner": o.get("fact"),
                    "source_document": o.get("filename"),
                    "evidence": o.get("evidence"),
                })

        # Risks
        report_risks = []
        for ritem in extracted:
            if ritem.get("category") == "risks":
                report_risks.append({
                    "risk": ritem.get("fact"),
                    "owner": None,
                    "source_document": ritem.get("filename"),
                    "evidence": ritem.get("evidence"),
                })

        # Decisions (from extracted decisions + reviewed conflicts)
        report_decisions = []
        for ditem in extracted:
            if ditem.get("category") == "decisions":
                report_decisions.append({
                    "decision": ditem.get("fact"),
                    "source_document": ditem.get("filename"),
                    "evidence": ditem.get("evidence"),
                    "human_reviewed": False,
                })

        # Include reviewed conflicts as decisions too
        for c in conflicts:
            if c.get("status") in ("resolved", "rejected"):
                report_decisions.append({
                    "decision": c.get("decision"),
                    "accepted_fact": c.get("accepted_fact"),
                    "review_status": c.get("status"),
                    "review_comment": c.get("review_comment"),
                    "source_evidence": {
                        "a": {"source": c.get("source_a"), "evidence": c.get("evidence_a")},
                        "b": {"source": c.get("source_b"), "evidence": c.get("evidence_b")},
                    },
                })

        # Action items
        report_actions = []
        for a in extracted:
            if a.get("category") == "action_items":
                report_actions.append({
                    "action": a.get("fact"),
                    "owner": None,
                    "due_date": None,
                    "source_document": a.get("filename"),
                    "evidence": a.get("evidence"),
                })

        # Conflicts output - include all conflicts with required fields
        report_conflicts = []
        for c in conflicts:
            report_conflicts.append({
                "conflict_id": c.get("conflict_id"),
                "description": c.get("description"),
                "status": c.get("status"),
                "decision": c.get("decision"),
                "accepted_fact": c.get("accepted_fact"),
                "source_a": c.get("source_a"),
                "evidence_a": c.get("evidence_a"),
                "source_b": c.get("source_b"),
                "evidence_b": c.get("evidence_b"),
            })

        report = {
            "run_id": run.run_id,
            "status": run.status,
            "project_overview": None,
            "milestones": report_milestones,
            "owners": report_owners,
            "risks": report_risks,
            "decisions": report_decisions,
            "action_items": report_actions,
            "facts": extracted,
            "conflicts": report_conflicts,
        }

        return JSONResponse(status_code=200, content=report)
    finally:
        db.close()


@app.post("/runs/{run_id}/examine")
def examine_run_endpoint(run_id: str, body: dict = Body(...)):
    rules = body.get("rules")
    if not isinstance(rules, list):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="rules must be a list")

    db = SessionLocal()
    try:
        run = db.query(Run).filter(Run.run_id == run_id).first()
        if not run:
            return JSONResponse(status_code=404, content={"error": "run not found"})

        if run.status == "running":
            run = _resume_run_if_needed(run, db)

        if run.status != "completed" or not run.draft:
            return JSONResponse(status_code=409, content={"error": "run must be completed with a draft before examination"})

        documents = []
        if run.project_id is not None:
            documents = db.query(Document).filter(Document.project_id == run.project_id).all()

        source_evidence = []
        for doc in documents:
            content = doc.content or ""
            if not content:
                continue
            source_evidence.append({
                "source_document": doc.filename or "unknown",
                "evidence": content,
            })

        try:
            result, llm_metrics = examine_run(rules, source_evidence, run.draft, include_metrics=True)
        except Exception as exc:
            from app.agents.examine_agent import ExamineUnavailableError

            if isinstance(exc, ExamineUnavailableError):
                llm_metrics = getattr(exc, "llm_metrics", None)
                result = {
                    "findings": [],
                    "examine_status": "unavailable",
                    "message": f"Examination unavailable because the LLM rate limit was reached. {str(exc)}",
                }
                run = _save_examine_state(db, run, result)
                run = _save_examine_metric(db, run, llm_metrics)
                return JSONResponse(status_code=200, content=result)
            raise

        run = _save_examine_state(db, run, result)
        run = _save_examine_metric(db, run, llm_metrics)
        return JSONResponse(status_code=200, content=result)
    finally:
        db.close()


@app.get("/runs/{run_id}/findings")
def get_findings(run_id: str):
    db = SessionLocal()
    try:
        run = db.query(Run).filter(Run.run_id == run_id).first()
        if not run:
            return JSONResponse(status_code=404, content={"error": "run not found"})

        if run.status == "running":
            run = _resume_run_if_needed(run, db)

        examine_state = copy.deepcopy(_get_examine_state(run))
        findings = examine_state.get("findings", [])
        examine_status = examine_state.get("examine_status", "clean")
        return JSONResponse(status_code=200, content={"findings": findings, "examine_status": examine_status})
    finally:
        db.close()


@app.post("/runs/{run_id}/findings/{finding_id}/review")
def review_finding(run_id: str, finding_id: str, body: dict = Body(...)):
    decision = body.get("decision")
    comment = body.get("comment")
    if decision not in {"approve", "reject"}:
        return JSONResponse(status_code=422, content={"error": "invalid decision"})

    db = SessionLocal()
    try:
        run = db.query(Run).filter(Run.run_id == run_id).first()
        if not run:
            return JSONResponse(status_code=404, content={"error": "run not found"})

        examine_state = copy.deepcopy(_get_examine_state(run))
        findings = examine_state.get("findings", [])
        if not isinstance(findings, list):
            return JSONResponse(status_code=404, content={"error": "finding not found"})

        found = False
        updated_findings = []
        now_iso = datetime.utcnow().isoformat()

        for finding in findings:
            if finding.get("finding_id") != finding_id:
                updated_findings.append(finding)
                continue

            found = True
            if finding.get("status") != "pending_review":
                return JSONResponse(status_code=409, content={"error": "finding already reviewed"})

            updated = dict(finding)
            updated["status"] = "approved" if decision == "approve" else "rejected"
            updated["decision"] = decision
            updated["review_comment"] = comment
            updated["reviewed_at"] = now_iso
            updated_findings.append(updated)

        if not found:
            return JSONResponse(status_code=404, content={"error": "finding not found"})

        examine_state["findings"] = updated_findings
        if not updated_findings:
            examine_state["examine_status"] = "clean"
        run = _save_examine_state(db, run, examine_state)
        return JSONResponse(status_code=200, content={"result": "review recorded"})
    finally:
        db.close()


@app.post("/runs/{run_id}/conflicts/{conflict_id}/review")
def review_conflict(run_id: str, conflict_id: str, body: dict = Body(...)):
    """Human reviewer records a decision on a conflict."""
    VALID = {"accept_a", "accept_b", "reject_conflict"}
    decision = body.get("decision")
    comment = body.get("comment")

    if decision not in VALID:
        return JSONResponse(status_code=422, content={"error": "invalid decision"})

    db = SessionLocal()
    try:
        run = db.query(Run).filter(Run.run_id == run_id).first()
        if not run:
            return JSONResponse(status_code=404, content={"error": "run not found"})

        conflicts = run.conflicts or []
        found = False
        new_conflicts = []
        now_iso = datetime.utcnow().isoformat()

        for c in conflicts:
            if c.get("conflict_id") != conflict_id:
                new_conflicts.append(c)
                continue
            # target conflict
            found = True
            if c.get("status") not in ("pending_review", None):
                return JSONResponse(status_code=409, content={"error": "conflict already reviewed"})

            updated = dict(c)
            if decision == "accept_a":
                updated["status"] = "resolved"
                updated["decision"] = "accept_a"
                updated["accepted_fact"] = updated.get("fact_a")
                updated["review_comment"] = comment
                updated["reviewed_at"] = now_iso
            elif decision == "accept_b":
                updated["status"] = "resolved"
                updated["decision"] = "accept_b"
                updated["accepted_fact"] = updated.get("fact_b")
                updated["review_comment"] = comment
                updated["reviewed_at"] = now_iso
            else:
                updated["status"] = "rejected"
                updated["decision"] = "reject_conflict"
                updated["review_comment"] = comment
                updated["reviewed_at"] = now_iso

            new_conflicts.append(updated)

        if not found:
            return JSONResponse(status_code=404, content={"error": "conflict not found"})

        # Also update draft conflicts if present
        draft = run.draft or {}
        if isinstance(draft, dict) and "conflicts" in draft:
            new_draft_conflicts = []
            for dc in draft["conflicts"]:
                if dc.get("conflict_id") == conflict_id:
                    # replace with updated version
                    for nc in new_conflicts:
                        if nc.get("conflict_id") == conflict_id:
                            new_draft_conflicts.append(nc)
                            break
                else:
                    new_draft_conflicts.append(dc)
            draft["conflicts"] = new_draft_conflicts

        all_reviewed = _all_conflicts_reviewed(new_conflicts)
        if all_reviewed:
            resolved_extracted_facts = _apply_conflict_reviews_to_facts(run.extracted_facts or [], new_conflicts)
            # Resume only the final graph transition. Retrieval, extraction and
            # comparison are explicitly supplied as completed persisted state.
            final_state = WORKFLOW_GRAPH.invoke({
                "run_id": run.run_id,
                "project_id": run.project_id,
                "extracted_facts": resolved_extracted_facts,
                "retrieved_contexts": run.retrieved_contexts or [],
                "conflicts": new_conflicts,
                "document_ids": _get_run_metadata(run.stages).get("document_ids", []),
                "query": _get_run_metadata(run.stages).get("query", ""),
                "top_k": _get_run_metadata(run.stages).get("top_k", 5),
                "completed_stages": ["LOAD_DOCUMENTS", "RETRIEVE_RELEVANT_CONTEXT", "EXTRACT_FACTS", "COMPARE_FACTS"],
            })
            db.refresh(run)
            final_draft = final_state.get("draft") or {}
            metadata = _get_run_metadata(run.stages)
            base_run_id = metadata.get("base_run_id")
            if base_run_id:
                base_run = db.query(Run).filter(Run.run_id == base_run_id, Run.project_id == run.project_id).first()
                incremental_sources = {
                    str(ctx.get("source_filename") or "").strip()
                    for ctx in (run.retrieved_contexts or [])
                    if ctx.get("source_filename")
                }
                changed_facts = [
                    fact for fact in (run.extracted_facts or [])
                    if (fact.get("source_document") or fact.get("filename")) in incremental_sources
                ]
                final_draft = build_incremental_draft(base_run.draft if base_run else None, resolved_extracted_facts, new_conflicts, changed_facts)
            elif not final_draft.get("facts"):
                final_draft = create_draft(resolved_extracted_facts, new_conflicts)
            run.status = "completed"
            run.current_stage = "COMPLETED"
            run.stages = _merge_stages_with_metadata({s: "completed" for s in STAGES}, _get_run_metadata(run.stages))
            run.conflicts = new_conflicts
            run.extracted_facts = resolved_extracted_facts
            run.draft = final_draft
        else:
            run.status = "waiting_for_review"
            run.current_stage = "WAITING_FOR_REVIEW"
            run.stages = _merge_stages_with_metadata({**(run.stages or {}), "WAITING_FOR_REVIEW": "in_progress"}, _get_run_metadata(run.stages))
            run.conflicts = new_conflicts
            try:
                run.draft = dict(draft) if isinstance(draft, dict) else draft
            except Exception:
                run.draft = draft

        # commit directly so JSON changes are persisted
        run.updated_at = datetime.utcnow()
        db.add(run)
        db.commit()
        db.refresh(run)

        return JSONResponse(status_code=200, content={"result": "review recorded"})
    finally:
        db.close()

