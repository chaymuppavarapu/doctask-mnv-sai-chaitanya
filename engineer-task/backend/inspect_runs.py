import json
from app.db import SessionLocal
from app.models.run import Run
from app.models.project import Project
from app.models.document import Document
from sqlalchemy import desc
with SessionLocal() as db:
    projects = db.query(Project).all()
    print('PROJECTS:')
    for p in projects:
        print(p.id, p.name)
    print('---')
    runs = db.query(Run).order_by(desc(Run.created_at)).all()
    for run in runs:
        sources = [ctx.get('source_filename') for ctx in run.retrieved_contexts or []]
        print(run.run_id, run.project_id, run.status, run.current_stage, len(run.extracted_facts or []), len(run.conflicts or []), sources)
    if runs:
        run = runs[0]
        print('LATEST')
        print(json.dumps({'run_id': run.run_id, 'project_id': run.project_id, 'retrieved_contexts': run.retrieved_contexts, 'extracted_facts': run.extracted_facts, 'conflicts': run.conflicts, 'draft': run.draft}, indent=2, ensure_ascii=False))
