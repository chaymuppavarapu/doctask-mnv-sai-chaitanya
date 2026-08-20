# SuperDocs Task 3 — Document Workflow Research Index

A static, Vercel-ready research interface for the final Task 3 dataset.

## Research model

Each row is deliberately structured as:

**Company → specific document workflow → recurring problem → buyer → where they listen → conversation opener → official evidence**

The final dataset uses one named company per row so that each row has a defensible primary evidence URL.

## Dataset

`use_cases.csv` contains 10 researched rows with:

- `use_case`
- `real_companies`
- `document_workflow`
- `recurring_problem`
- `evidence_basis`
- `buyer_role`
- `why_it_bites`
- `where_they_listen`
- `conversation_opener`
- `source_url`

## Run locally

No build step is required.

```powershell
python -m http.server 8080
```

Open `http://localhost:8080`.

## Deploy to Vercel

```powershell
npm install -g vercel
vercel
vercel --prod
```

No environment variables are required.

## CSV upload

The UI includes **Upload CSV**. The uploaded CSV must contain the same column names as `use_cases.csv`. The browser parses the CSV locally; no data is sent to a backend.

## Submission evidence

For the Task 3 demo, show:

1. Deployed public URL
2. 10-row index
3. Search/filter
4. One or two detailed research cards
5. Official source link for each selected company
6. The company → workflow → pain → buyer → conversation chain
7. CSV upload
8. Mobile/responsive view
