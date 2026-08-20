import math
import os
import re
from datetime import datetime
from pathlib import Path
from typing import Any

from langgraph import graph
from langchain_core.runnables import RunnableConfig
from sqlalchemy import text
from sqlalchemy.orm import Session

try:
    from sentence_transformers import SentenceTransformer
except Exception:  # pragma: no cover - fallback for environments without the package
    SentenceTransformer = None

from app.db import SessionLocal
from app.models.document import Document, DocumentChunk
from app.models.project import Project

MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"
EMBED_DIM = 384
MODEL: SentenceTransformer | None = None


class _FallbackSentenceTransformer:
    """Lightweight deterministic embedding fallback used in test and offline environments."""

    def encode(self, texts: list[str], normalize_embeddings: bool = True) -> list[list[float]]:
        embeddings: list[list[float]] = []
        for text in texts:
            tokens = re.findall(r"\w+", text.lower())
            if not tokens:
                embeddings.append([0.0] * 8)
                continue

            values = [0.0] * 8
            for index, token in enumerate(tokens[:16]):
                weight = 1.0 + (index % 8)
                values[index % 8] += len(token) * weight

            if normalize_embeddings:
                norm = math.sqrt(sum(value * value for value in values))
                if norm:
                    values = [value / norm for value in values]

            embeddings.append(values)

        return embeddings


def _load_model() -> SentenceTransformer | _FallbackSentenceTransformer:
    global MODEL
    if MODEL is None:
        if SentenceTransformer is None:
            MODEL = _FallbackSentenceTransformer()
            return MODEL

        # Prefer the locally cached Hugging Face snapshot when available.
        cache_snapshot = Path.home() / ".cache" / "huggingface" / "hub" / "models--sentence-transformers--all-MiniLM-L6-v2" / "snapshots"
        try:
            if cache_snapshot.exists():
                latest_snapshot = None
                for child in cache_snapshot.iterdir():
                    if child.is_dir():
                        latest_snapshot = child
                        break
                if latest_snapshot is not None:
                    MODEL = SentenceTransformer(str(latest_snapshot), cache_folder=str(cache_snapshot))
                else:
                    MODEL = SentenceTransformer(MODEL_NAME, cache_folder=str(cache_snapshot))
            else:
                MODEL = SentenceTransformer(MODEL_NAME)
        except Exception:
            MODEL = _FallbackSentenceTransformer()
    return MODEL

SAMPLE_FILENAMES = [
    "apollo_project_plan.txt",
    "apollo_week1_status.txt",
    "apollo_sprint_meeting.txt",
]


def deterministic_chunk_text(text: str, max_words: int = 120, overlap: int = 20) -> list[str]:
    words = [w for w in text.strip().split() if w]
    if not words:
        return []

    if overlap >= max_words:
        overlap = max_words - 1

    chunks: list[str] = []
    start = 0

    while start < len(words):
        end = min(start + max_words, len(words))
        chunk = " ".join(words[start:end]).strip()
        if chunk:
            chunks.append(chunk)
        if end == len(words):
            break
        start += max_words - overlap

    return chunks


def pg_vector_literal(embedding: list[float]) -> str:
    return "[" + ",".join(repr(float(value)) for value in embedding) + "]"


def embed_texts(texts: list[str]) -> list[list[float]]:
    if not texts:
        return []
    model = _load_model()
    embeddings = model.encode(texts, normalize_embeddings=True)
    return [[float(x) for x in emb] for emb in embeddings]


def index_document_chunks(db: Session, document: Document) -> list[DocumentChunk]:
    db.query(DocumentChunk).filter(DocumentChunk.document_id == document.id).delete(synchronize_session=False)
    chunk_texts = deterministic_chunk_text(document.content or "")
    embeddings = embed_texts(chunk_texts)

    chunks: list[DocumentChunk] = []
    for index, (text, embedding) in enumerate(zip(chunk_texts, embeddings)):
        chunk = DocumentChunk(
            document_id=document.id,
            chunk_index=index,
            text=text,
            embedding=embedding,
            created_at=datetime.utcnow(),
        )
        db.add(chunk)
        chunks.append(chunk)

    db.commit()
    return chunks


def retrieve_relevant_chunks(query: str, project_id: int, top_k: int = 5, document_ids: list[int] | None = None) -> list[dict[str, Any]]:
    embedding = embed_texts([query])
    if not embedding:
        return []
    vector_literal = pg_vector_literal(embedding[0])

    where_clauses = ["d.project_id = :project_id"]
    params: dict[str, Any] = {"top_k": top_k, "project_id": project_id}
    if document_ids:
        where_clauses.append("d.id = ANY(:document_ids)")
        params["document_ids"] = document_ids

    where_clause = "WHERE " + " AND ".join(where_clauses)

    sql = text(
        f"""
        SELECT c.id,
               c.document_id,
               c.chunk_index,
               c.text,
               d.filename AS source_filename,
               c.embedding <=> '{vector_literal}'::vector AS distance
        FROM document_chunks AS c
        JOIN documents AS d ON d.id = c.document_id
        {where_clause}
        ORDER BY distance ASC, c.id ASC
        LIMIT :top_k
        """
    )

    with SessionLocal() as db:
        rows = db.execute(sql, params).mappings().all()

    results: list[dict[str, Any]] = []
    for row in rows:
        distance = float(row["distance"])
        results.append(
            {
                "id": row["id"],
                "document_id": row["document_id"],
                "chunk_index": row["chunk_index"],
                "text": row["text"],
                "source_filename": row["source_filename"],
                "similarity_score": 1.0 / (1.0 + distance),
                "distance": distance,
            }
        )

    return results


def load_sample_documents() -> list[Document]:
    base_dir = Path(__file__).resolve().parents[2]
    sample_dir = base_dir / "sample-data"
    if not sample_dir.exists():
        return []

    loaded: list[Document] = []
    with SessionLocal() as db:
        project = db.query(Project).filter(Project.name == "Apollo Sample").first()
        if project is None:
            project = Project(name="Apollo Sample")
            db.add(project)
            db.commit()
            db.refresh(project)

        for filename in SAMPLE_FILENAMES:
            path = sample_dir / filename
            if not path.exists():
                continue

            document = (
                db.query(Document)
                .filter(Document.filename == filename, Document.project_id == project.id)
                .first()
            )
            if document is None:
                content = path.read_text(encoding="utf-8")
                document = Document(
                    project_id=project.id,
                    filename=filename,
                    document_type="sample",
                    content=content,
                )
                db.add(document)
                db.commit()
                db.refresh(document)

            chunk_count = db.query(DocumentChunk).filter(DocumentChunk.document_id == document.id).count()
            if chunk_count == 0:
                index_document_chunks(db, document)

            loaded.append(document)

    return loaded


class SearchState(dict):
    pass


def _embed_query(state: SearchState, config: RunnableConfig | None = None) -> dict[str, list[float]]:
    query = state.get("query", "")
    return {
        "embedding": embed_texts([query])[0],
        "project_id": state.get("project_id"),
        "document_ids": state.get("document_ids"),
        "top_k": state.get("top_k", 5),
    }


def _search_chunks(state: SearchState, config: RunnableConfig | None = None) -> dict[str, list[dict[str, Any]]]:
    embedding = state.get("embedding")
    if not embedding:
        return {"results": []}
    results = retrieve_relevant_chunks_from_embedding(
        embedding,
        state.get("top_k", 5),
        project_id=state.get("project_id"),
        document_ids=state.get("document_ids"),
    )
    return {"results": results}


def retrieve_relevant_chunks_from_embedding(
    embedding: list[float],
    top_k: int = 5,
    project_id: int | None = None,
    document_ids: list[int] | None = None,
) -> list[dict[str, Any]]:
    vector_literal = pg_vector_literal(embedding)
    where_clauses = []
    params: dict[str, Any] = {"top_k": top_k}
    if project_id is not None:
        where_clauses.append("d.project_id = :project_id")
        params["project_id"] = project_id
    if document_ids:
        where_clauses.append("d.id = ANY(:document_ids)")
        params["document_ids"] = document_ids

    where_clause = ""
    if where_clauses:
        where_clause = "WHERE " + " AND ".join(where_clauses)

    sql = text(
        f"""
        SELECT c.id,
               c.document_id,
               c.chunk_index,
               c.text,
               d.filename AS source_filename,
               c.embedding <=> '{vector_literal}'::vector AS distance
        FROM document_chunks AS c
        JOIN documents AS d ON d.id = c.document_id
        {where_clause}
        ORDER BY distance ASC, c.id ASC
        LIMIT :top_k
        """
    )

    with SessionLocal() as db:
        rows = db.execute(sql, params).mappings().all()

    results: list[dict[str, Any]] = []
    for row in rows:
        distance = float(row["distance"])
        results.append(
            {
                "id": row["id"],
                "document_id": row["document_id"],
                "chunk_index": row["chunk_index"],
                "text": row["text"],
                "source_filename": row["source_filename"],
                "similarity_score": 1.0 / (1.0 + distance),
                "distance": distance,
            }
        )
    return results


def build_search_graph() -> graph.StateGraph:
    builder = graph.StateGraph(dict)
    builder.add_node("embed_query", _embed_query)
    builder.add_node("search_chunks", _search_chunks)
    builder.add_edge(graph.START, "embed_query")
    builder.add_edge("embed_query", "search_chunks")
    builder.set_entry_point("embed_query")
    builder.set_finish_point("search_chunks")
    return builder.compile()

SEARCH_GRAPH = build_search_graph()


def search(query: str, project_id: int, top_k: int = 5) -> list[dict[str, Any]]:
    state = {"query": query, "project_id": project_id, "top_k": top_k}
    output = SEARCH_GRAPH.invoke(state)
    return output.get("results", [])
