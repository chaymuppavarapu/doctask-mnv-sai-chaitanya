https://superdocs-portfolio.vercel.app/  (we will get a clear picture what i have build.by this the chaos will be less of finding the tasks. this single is everything about the task)

# DocTask — Project Intelligence

DocTask turns a project’s collection of documents into an evidence-grounded intelligence system. It retrieves relevant context, extracts structured facts, detects contradictions, pauses for human review when needed, and preserves the source evidence behind the final report.

The workflow is intentionally conservative: documents flow into retrieval, facts are normalized, conflicting values are surfaced for review, and the approved result becomes the project’s report rather than silently overwriting earlier evidence.

## Problem

Project information is often distributed across plans, milestone notes, sprint updates, and follow-up documents. The same milestone can appear with different owners, dates, or statuses across sources, and those differences matter when a team needs a trustworthy summary.

A useful system must therefore:

- retrieve the most relevant evidence for a project
- normalize equivalent facts across documents
- detect contradictory values
- show the supporting evidence for each conclusion
- pause for human review when disagreements exist
- preserve approved outputs for later inspection
- support incremental updates without rewriting unrelated report content
- recover from interrupted runs without losing completed work

## What DocTask Does

| Capability | What it does |
| --- | --- |
| Project and document management | Create projects, upload documents, list documents, and inspect project-level changes. |
| Evidence-grounded retrieval | Retrieve project-scoped document chunks using semantic similarity over indexed document content. |
| Structured fact extraction | Extract milestone, owner, date, risk, decision, and action-item facts from retrieved context. |
| Canonicalization | Normalize equivalent labels and subject references so downstream comparison behaves consistently. |
| Conflict detection | Identify conflicting facts across evidence and surface them as reviewable conflicts. |
| Human review gate | Require explicit review decisions before a run can complete with a final report. |
| Incremental updates | Reuse a completed base run and process only newly introduced documents and impacted facts. |
| Change ledger | Record project-level change events and changed subject/fact-type values over time. |
| Crash/resume | Persist stage outputs and resume a run from the incomplete stage instead of restarting from scratch. |
| Concurrent run isolation | Keep retrieval, extracted facts, conflicts, drafts, and review state isolated per run. |
| Examine | Run a post-analysis validation pass and record findings or an unavailable-status outcome. |
| Watch folder | Ingest new UTF-8 text documents dropped into a project-specific watch folder. |
| MCP interface | Expose key workflow operations over Streamable HTTP for external clients. |
| Run telemetry | Track per-stage timing, token usage, and estimated cost when available. |
| Prompt-injection/data isolation | Treat instructions embedded in documents as data rather than workflow commands. |

## Architecture

```mermaid
flowchart TD
    A[React Dashboard] --> B[FastAPI API]
    B --> C[PostgreSQL + pgvector]
    B --> D[Compiled LangGraph Workflow]
    D --> D1[Load Documents]
    D --> D2[Retrieve Relevant Context]
    D --> D3[Extract Facts]
    D --> D4[Canonicalize Facts]
    D --> D5[Compare Facts]
    D --> D6[Human Review Gate]
    D --> D7[Create Draft / Report]
    D7 --> E[Project Report]
    E --> F[Examine]

    G[Watch Folder] --> H[Upload / Indexing]
    H --> C

    I[MCP Client] --> J[MCP Server]
    J --> B
```

The backend persists runs, documents, change records, and run-stage state in PostgreSQL. The workflow itself is compiled in LangGraph and coordinated by the FastAPI application.

## Analysis Workflow

### 1. Load Documents
The run begins by validating the selected project and document set. Documents are loaded from the database and become the evidence base for the run.

### 2. Retrieve Relevant Context
Rather than sending every document to the LLM, the system uses project-scoped semantic retrieval over indexed chunks. This keeps the downstream extraction step focused on the evidence most likely to matter for the current query.

### 3. Extract Facts
The workflow extracts structured facts from retrieved context. In the current implementation this is driven by the Groq-backed extraction logic and produces facts such as milestones, owners, dates, decisions, risks, and action items.

### 4. Canonicalize Facts
Equivalent values are normalized before comparison. Examples include mapping labels such as "due date" to a canonical `due_date` field, associating owner facts with their milestone subject, and aligning equivalent milestone names. This reduces LLM variability and makes downstream comparison more stable.

### 5. Compare Facts
The comparison step looks for conflicting values across extracted facts. A simple concrete example is:

- API Integration due date from one source: `2026-08-20`
- API Integration due date from another source: `2026-08-29`

Those are surfaced as a reviewable conflict rather than silently merged.

### 6. Human Review
If conflicts are found, the run enters `waiting_for_review`. The API exposes review actions via `/runs/{run_id}/conflicts/{conflict_id}/review` with `accept_a`, `accept_b`, or `reject_conflict`. The report is not exposed as a fully resolved final report until the conflicting facts are reviewed.

### 7. Create Draft / Final Report
Once conflicts have been resolved, the workflow generates a grounded draft. The report preserves milestone summaries, owners, dates, and evidence provenance, and it ties each conclusion back to the source document and supporting evidence.

### 8. Examine
After a completed run is available, the Examine path can validate the report against a set of user-supplied rules. It returns results in one of three states:

- `clean` when no findings are produced
- `findings` when issues are detected
- `unavailable` when the validation step cannot run because the provider is unavailable or rate-limited

## Incremental Updates

Incremental runs are supported when a completed base run is supplied. In that mode:

- only newly added documents are retrieved and extracted
- only impacted facts are considered for change propagation
- unaffected facts remain intact
- changed values create old/new change records
- contradictions enter human review if they affect the same canonical entity
- accepted changes update the draft without rewriting unrelated fields

A concrete example is a milestone moving from `2026-09-25` to `2026-10-02`. The new run records the change, surfaces the difference for review, and preserves the rest of the report unless the review explicitly changes the affected entity.

The baseline run remains unchanged until the incremental run is reviewed and finalized.

## Durability and Recovery

Run state, stage outputs, and relevant metadata are persisted in PostgreSQL. If a run is interrupted, completed stages remain persisted and the next read of the run can resume from the incomplete stage rather than re-running completed retrieval or extraction work.

This is best described as persisted-stage recovery and resume rather than a LangGraph checkpointer.

## Concurrency and Isolation

Independent runs maintain isolated retrieval contexts, extracted facts, conflicts, drafts, and review decisions. The behavior suite includes concurrent Apollo/Phoenix-style runs to confirm that project state remains isolated per workflow execution.

## Evidence Grounding

The system is designed around an evidence chain:

Report field → canonical fact → source document → source evidence

That structure makes it possible to explain why a milestone owner or due date appears in the report and to preserve the evidence used to support it.

## Prompt Injection / Document Safety

Instructions found inside uploaded documents are treated as document data, not workflow commands. The repository includes a behavior test that verifies document instructions do not control the workflow. This is a practical guardrail rather than a claim of complete enterprise-grade prompt-injection defense.

## Observability and Cost Accounting

Runs expose timing and stage-level metrics. The implementation records:

- total run duration
- per-stage duration
- input tokens when available
- output tokens when available
- total tokens when available
- estimated cost when pricing information is available

The configuration file supports the following environment variables:

- `DATABASE_URL`
- `GROQ_API_KEY`
- `GROQ_MODEL`
- `LLM_INPUT_COST_PER_1M`
- `LLM_OUTPUT_COST_PER_1M`

Deterministic stages do not necessarily report token or cost values because they do not invoke the LLM. Provider failures do not fabricate metrics.

## Watch Folder

The local watcher is implemented in `engineer-task/backend/watch_folder.py` and scans a project directory under `engineer-task/watch/<project_id>/` for new files. It currently supports UTF-8 `.txt` documents only.

Example:

```powershell
cd engineer-task/backend
.venv\Scripts\python.exe watch_folder.py --root ..\watch
```

## MCP

DocTask exposes a lightweight MCP server in `engineer-task/backend/mcp_server.py` and a runnable example client in `engineer-task/backend/mcp_client_example.py`. The server uses Streamable HTTP and exposes operations for:

- listing documents
- searching documents
- creating analysis runs
- reading run state
- reading reports
- reviewing conflicts
- examining runs
- listing findings
- reviewing findings

Start the server:

```powershell
cd engineer-task/backend
.venv\Scripts\python.exe mcp_server.py
```

Run the example client in a second terminal:

```powershell
cd engineer-task/backend
.venv\Scripts\python.exe mcp_client_example.py --project-id 1 --document-ids 1 2
```

MCP execution is implemented, but provider-backed end-to-end execution may still be environment-dependent.

## API / Machine Interface

The FastAPI backend exposes the primary project workflow through a small set of resource-oriented endpoints. The main categories are:

- Projects: `POST /projects`, `GET /projects`, `GET /projects/{project_id}`
- Documents: `POST /projects/{project_id}/documents/upload`, `POST /documents`, `GET /documents`, `GET /projects/{project_id}/documents`
- Changes: `GET /projects/{project_id}/changes`
- Search: `POST /search`
- Runs: `POST /runs`, `GET /runs/{run_id}`
- Reports: `GET /runs/{run_id}/report`
- Conflicts: `POST /runs/{run_id}/conflicts/{conflict_id}/review`
- Examine: `POST /runs/{run_id}/examine`, `GET /runs/{run_id}/findings`, `POST /runs/{run_id}/findings/{finding_id}/review`

## Frontend

The frontend is a React + Vite dashboard. It provides project navigation, document management, run status, workflow stage visibility, human review controls, Examine results, run metrics, evidence inspection, and change visibility.

## Technology Stack

| Layer | Technologies |
| --- | --- |
| Frontend | React, Vite |
| Backend | FastAPI, Python |
| Workflow | LangGraph |
| Database | PostgreSQL, pgvector |
| Retrieval | Semantic embedding retrieval with sentence-transformers |
| LLM | Groq |
| Testing | Python `unittest` |
| Integration | MCP, watch-folder ingestion |

## Project Structure

```text
backend/
  app/
    agents/
    models/
    config.py
    db.py
    facts.py
    groq_client.py
    incremental.py
    main.py
    semantic.py
  tests/
  mcp_server.py
  mcp_client_example.py
  watch_folder.py
frontend/
  src/
  package.json
engineer-task/sample-data/
watch/
README.md
```

Key implementation files:

- `engineer-task/backend/app/main.py` orchestrates projects, documents, runs, reports, conflicts, Examine, and incremental updates.
- `engineer-task/backend/app/semantic.py` handles chunking, embedding, indexing, and semantic retrieval.
- `engineer-task/backend/app/facts.py` and `engineer-task/backend/app/incremental.py` handle canonicalization and incremental change logic.
- `engineer-task/backend/app/agents/` contains the extraction, conflict, draft, and examine agents.
- `engineer-task/backend/mcp_server.py` and `engineer-task/backend/mcp_client_example.py` provide the MCP surface.

## Setup

The repository is designed for a local Windows PowerShell workflow.

1. Clone the repository.
2. Create a Python environment in `engineer-task/backend/` and install dependencies:

```powershell
cd engineer-task/backend
.venv\Scripts\python.exe -m pip install -r requirements.txt
```

3. Create `engineer-task/backend/.env` and configure the local environment variables:

```env
DATABASE_URL=postgresql+psycopg://USER:PASSWORD@HOST:5432/DBNAME
GROQ_API_KEY=your_key_here
GROQ_MODEL=openai/gpt-oss-120b
LLM_INPUT_COST_PER_1M=0
LLM_OUTPUT_COST_PER_1M=0
```

4. Start a PostgreSQL instance reachable by `DATABASE_URL`.
5. Start the FastAPI backend:

```powershell
cd engineer-task/backend
.venv\Scripts\python.exe -m uvicorn app.main:app --reload
```

6. Install and start the frontend:

```powershell
cd engineer-task/frontend
npm install
npm run dev
```

## Testing

The verified backend test command is:

```powershell
cd engineer-task/backend
.venv\Scripts\python.exe -m unittest discover -s tests -v
```

The current behavior suite contains 28 passing tests and covers:

- conflicts and human review
- incremental updates
- crash/resume behavior
- concurrent run isolation
- prompt-injection/data separation
- metrics and cost accounting
- provider failure handling
- canonicalization
- Examine behavior

The frontend build command is:

```powershell
cd engineer-task/frontend
npm run build
```

## Demo Flow

A realistic evaluator-friendly demo is:

1. Create or open a project and upload source documents.
2. Run analysis and inspect the workflow stages.
3. Observe the run metrics and stage timing.
4. Review a detected conflict and compare the opposing facts and evidence.
5. Accept the preferred value and observe the completed report.
6. Run Examine to validate the output against a rule set.
7. Add a follow-up document or drop one into `engineer-task/watch/<project_id>/`.
8. Run an incremental update and show that only affected facts change while unrelated fields remain intact.

## Verification Status

| Area | Status |
| --- | --- |
| Backend tests | PASS |
| Frontend build | PASS |
| Human review flow | PASS (behavior-tested) |
| Incremental conflict update | PASS (behavior-tested) |
| Concurrent isolation | PASS (behavior-tested) |
| Crash/resume | PASS (behavior-tested) |
| Metrics and cost accounting | PASS (behavior-tested) |
| Prompt-injection/data separation | PASS (behavior-tested) |
| Watch folder | Implemented; limited to UTF-8 `.txt` files |
| MCP | Implemented; provider-backed end-to-end execution may be environment-limited |

## Known Limitations

The current implementation is functional, but a few limitations remain:

- MCP end-to-end execution depends on the local environment and provider availability.
- The watch folder currently accepts UTF-8 `.txt` files only.
- The semantic retrieval and incremental impact logic are intentionally scoped to the current repository’s workflow and tests.
- `datetime.utcnow()` deprecation warnings are still present in the codebase.
- Token and cost values depend on provider responses and the environment configuration.

## Security / Secrets

- Keep `engineer-task/backend/.env` local to the development environment and do not commit it.
- Never commit API keys or other secrets.
- Uploaded document instructions are treated as data rather than workflow commands.
- The repository’s local environment/build artifacts are expected to stay out of source control.

## Submission

This README describes the current workspace state of the DocTask project. The repository itself is the source of truth for implementation details, workflow behavior, and verification status.


## Test Suite

The behavior suite contains 28 deterministic `unittest` cases. It does not require a developer database or LLM API key to run. The test module supplies a non-routable PostgreSQL test URL before importing the application; database calls are mocked where required.

```powershell
cd engineer-task/backend
.venv\Scripts\Activate.ps1
python -m unittest discover -s tests -v
```

A live PostgreSQL/pgvector `DATABASE_URL` and `GROQ_API_KEY` are required only for provider-backed application execution. Never commit `.env`; copy `.env.example` to `.env` locally and fill in private values.
