# SuperDocs Task 3 — Document Workflow Research Index

A static, Vercel-ready research interface for the final Task 3 dataset.

## Research model

Each row is deliberately structured as:

**Company → specific document workflow → recurring problem → buyer → where they listen → conversation opener → official evidence**

The index contains **10 fixed, curated research cases across 10 distinct real companies**. Each row uses one named company and a defensible official evidence URL. The deployed interface is intentionally fixed for evaluation: there is no CSV upload or runtime data replacement.

## Dataset

The canonical research dataset is stored in `use_cases.csv`. The UI embeds the same 10 rows directly in `app.js` so the deployed experience is deterministic and immediately reviewable.

Fields:

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

## Evaluation flow

The interface is designed for a fast evaluator review:

1. Open the deployed public URL
2. See the 10-row fixed research index
3. Search or filter the research
4. Open a detailed research card
5. Inspect the official evidence source
6. Follow the company → workflow → pain → buyer → conversation chain
7. Check the responsive/mobile layout

## Research boundary

This is research only. **No outreach was performed.** Companies and buyer roles are research targets, not contacted prospects.

## Final research set

The final index deliberately uses one distinct company per row to avoid duplicate-company rows and make buyer mapping easier to evaluate.
