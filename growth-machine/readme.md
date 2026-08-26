# Growth Machine

A runnable evidence-driven research, qualification, and personalization machine for identifying B2B SaaS accounts with document-heavy workflows and mapping only supported SuperDocs capabilities to those opportunities.

## Folders

- `app/` — Streamlit application and core research/qualification engine.
- `data/` — supplied public-evidence batches used as research inputs.
- `runs/` — measured research outputs from completed runs.
  - `run_001/` — first validated research run.
  - `run_002/` — second validated research run.
- `requirements.txt` — Python dependencies.
- `.gitignore` — excludes local/runtime artifacts.

## Run

From this directory:

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
streamlit run app/app.py
