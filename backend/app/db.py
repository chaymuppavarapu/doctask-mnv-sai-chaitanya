from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import sessionmaker
from app.models.base import Base
from app.models.document import Document, DocumentChunk
from app.models.project import Project
from app.models.run import Run
from app.models.change_record import ChangeRecord

from app.config import settings


engine = create_engine(
    settings.database_url,
    pool_pre_ping=True,
)

SessionLocal = sessionmaker(
    bind=engine,
    autoflush=False,
    autocommit=False,
    expire_on_commit=False,
)


def _ensure_analysis_runs_columns() -> None:
    inspector = inspect(engine)
    if "analysis_runs" not in inspector.get_table_names():
        return

    existing_columns = {column_info["name"] for column_info in inspector.get_columns("analysis_runs")}
    missing_columns = []

    if "retrieved_contexts" not in existing_columns:
        missing_columns.append("ALTER TABLE analysis_runs ADD COLUMN retrieved_contexts JSON")
    if "project_id" not in existing_columns:
        missing_columns.append("ALTER TABLE analysis_runs ADD COLUMN project_id INTEGER REFERENCES projects(id)")

    if missing_columns:
        with engine.begin() as connection:
            for ddl in missing_columns:
                connection.execute(text(ddl))


def _ensure_project_columns() -> None:
    inspector = inspect(engine)
    if "documents" not in inspector.get_table_names():
        return

    existing_columns = {column_info["name"] for column_info in inspector.get_columns("documents")}
    if "project_id" not in existing_columns:
        with engine.begin() as connection:
            connection.execute(text("ALTER TABLE documents ADD COLUMN project_id INTEGER REFERENCES projects(id)"))


def create_tables() -> None:
    """Create database tables for all models registered on `Base`.

    This is a tiny helper used at application startup.
    """
    Base.metadata.create_all(bind=engine)
    _ensure_project_columns()
    _ensure_analysis_runs_columns()
