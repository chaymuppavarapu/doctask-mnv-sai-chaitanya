from __future__ import annotations

import json
from typing import Any, Literal, Optional

import uvicorn
from mcp.server import MCPServer

from app.main import (
    create_run as create_run_endpoint,
    get_run as get_run_endpoint,
    get_run_report as get_report_endpoint,
    list_documents as list_documents_endpoint,
    review_conflict as review_conflict_endpoint,
    examine_run_endpoint as examine_run_endpoint,
    get_findings as get_findings_endpoint,
    review_finding as review_finding_endpoint,
)
from app.semantic import retrieve_relevant_chunks

server = MCPServer(
    name="Doctask MCP Server",
    title="Doctask MCP Server",
    description="Official MCP server exposing Doctask business logic via the MCP protocol.",
    version="1.0.0",
)


def _unwrap_response(response: Any) -> Any:
    if hasattr(response, "body"):
        try:
            return json.loads(response.body.decode("utf-8"))
        except Exception as exc:
            raise RuntimeError("Unable to decode JSONResponse") from exc
    return response


@server.tool(
    name="list_documents",
    title="List Documents",
    description="Returns the available uploaded documents, optionally scoped to a project.",
)
def list_documents(project_id: int | None = None) -> Any:
    return _unwrap_response(list_documents_endpoint(project_id=project_id))


@server.tool(
    name="search_documents",
    title="Search Documents",
    description="Search documents using semantic retrieval.",
)
def search_documents(query: str, project_id: int, top_k: int = 5) -> list[dict[str, Any]]:
    return retrieve_relevant_chunks(query, project_id=project_id, top_k=top_k)


@server.tool(
    name="create_analysis_run",
    title="Create Analysis Run",
    description="Starts the existing analysis workflow for the given documents and query.",
)
def create_analysis_run(
    project_id: int,
    document_ids: list[int],
    query: Optional[str] = None,
    top_k: int = 5,
) -> Any:
    response = create_run_endpoint(
        {"project_id": project_id, "document_ids": document_ids, "query": query, "top_k": top_k}
    )
    return _unwrap_response(response)


@server.tool(
    name="get_run",
    title="Get Run",
    description="Returns existing run status, stages, extracted facts, and conflicts.",
)
def get_run(run_id: str) -> Any:
    return _unwrap_response(get_run_endpoint(run_id))


@server.tool(
    name="review_conflict",
    title="Review Conflict",
    description="Records a human review decision on a conflict.",
)
def review_conflict(
    run_id: str,
    conflict_id: str,
    decision: Literal["accept_a", "accept_b", "reject"],
    comment: Optional[str] = None,
) -> Any:
    mapped_decision = "reject_conflict" if decision == "reject" else decision
    response = review_conflict_endpoint(
        run_id,
        conflict_id,
        {"decision": mapped_decision, "comment": comment},
    )
    return _unwrap_response(response)


@server.tool(
    name="get_report",
    title="Get Report",
    description="Returns the existing final report for a run.",
)
def get_report(run_id: str) -> Any:
    return _unwrap_response(get_report_endpoint(run_id))


@server.tool(
    name="examine_run",
    title="Examine Run",
    description="Evaluates a completed run against a set of user-provided rules and records findings.",
)
def examine_run(run_id: str, rules: list[str]) -> Any:
    return _unwrap_response(examine_run_endpoint(run_id, {"rules": rules}))


@server.tool(
    name="list_run_findings",
    title="List Run Findings",
    description="Returns the current examine findings and status for a run.",
)
def list_run_findings(run_id: str) -> Any:
    return _unwrap_response(get_findings_endpoint(run_id))


@server.tool(
    name="review_finding",
    title="Review Finding",
    description="Records a review decision on an examine finding.",
)
def review_finding(run_id: str, finding_id: str, decision: str, comment: str | None = None) -> Any:
    return _unwrap_response(review_finding_endpoint(run_id, finding_id, {"decision": decision, "comment": comment}))


app = server.streamable_http_app(streamable_http_path="/mcp", json_response=True)


if __name__ == "__main__":
    uvicorn.run("mcp_server:app", host="127.0.0.1", port=9001, reload=False)
