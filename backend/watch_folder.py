"""Simple local polling watcher for ``watch/<project_id>/`` text documents.

Run from ``backend``: ``.venv\\Scripts\\python.exe watch_folder.py --root ..\\watch``.
It deliberately uses the same Document model and indexing function as uploads.
"""
from __future__ import annotations

import argparse
import time
from pathlib import Path

from app.db import SessionLocal, create_tables
from app.main import _record_document_added
from app.models.document import Document
from app.models.project import Project
from app.semantic import index_document_chunks


SUPPORTED = {".txt"}


def ingest_new_files(root: Path) -> int:
    ingested = 0
    with SessionLocal() as db:
        for project_dir in root.iterdir() if root.exists() else []:
            if not project_dir.is_dir() or not project_dir.name.isdigit():
                continue
            project_id = int(project_dir.name)
            if not db.query(Project).filter(Project.id == project_id).first():
                continue
            for path in project_dir.iterdir():
                if not path.is_file() or path.suffix.lower() not in SUPPORTED:
                    continue
                exists = db.query(Document).filter(Document.project_id == project_id, Document.filename == path.name).first()
                if exists:
                    continue
                document = Document(project_id=project_id, filename=path.name, document_type=path.suffix[1:].lower(), content=path.read_text(encoding="utf-8"))
                db.add(document)
                db.commit()
                db.refresh(document)
                index_document_chunks(db, document)
                _record_document_added(db, project_id, document)
                ingested += 1
    return ingested


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default="../watch")
    parser.add_argument("--interval", type=float, default=2.0)
    args = parser.parse_args()
    root = Path(args.root)
    root.mkdir(parents=True, exist_ok=True)
    create_tables()
    print(f"Watching {root.resolve()} (Ctrl+C to stop)")
    while True:
        added = ingest_new_files(root)
        if added:
            print(f"Ingested {added} document(s)")
        time.sleep(args.interval)


if __name__ == "__main__":
    main()
