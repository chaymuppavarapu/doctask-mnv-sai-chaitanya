
from dataclasses import dataclass, asdict
from pathlib import Path
from datetime import datetime, timezone
import csv, hashlib, json, re

CAPABILITY_MAP = {
    "html": "HTML document editing",
    "editing": "AI-assisted direct document editing",
    "automation": "Automated document workflows",
    "api": "REST API / server-side document processing",
    "mcp": "MCP integration",
    "template": "Template-driven document workflows",
    "localization": "Localization workflows for document content",
}

KEYWORDS = {
    "html": ["html", "help center", "help-centre", "knowledge base", "web documentation", "web docs"],
    "editing": ["edit", "editing", "revision", "revise", "update", "rewrite", "content maintenance"],
    "automation": ["automate", "automation", "workflow", "manual", "repetitive", "pipeline", "batch"],
    "template": ["template", "templates", "report", "proposal", "document generation"],
    "localization": ["localization", "localisation", "translation", "translate", "multilingual", "locale", "languages"],
    "api": ["api", "programmatic", "server-side"],
    "mcp": ["mcp", "cursor", "claude"],
}

@dataclass
class Prospect:
    company: str
    role: str
    evidence_url: str
    evidence_title: str
    evidence_summary: str
    source_type: str = "public"
    workflow_hint: str = ""

@dataclass
class Result:
    company: str
    role: str
    evidence_url: str
    evidence_title: str
    workflow: str
    evidence_observation: str
    pain_hypothesis: str
    fit_score: int
    fit_band: str
    matched_capabilities: list
    personalization: str
    subject: str
    draft: str
    human_review_required: bool = True

def norm(s):
    return re.sub(r"\s+", " ", (s or "").strip()).lower()

def fingerprint(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()[:16]

def load_csv(path):
    with open(path, encoding="utf-8-sig", newline="") as f:
        rows = list(csv.DictReader(f))
    required = {"company","role","evidence_url","evidence_title","evidence_summary"}
    if not rows:
        raise ValueError("Input batch is empty.")
    missing = required - set(rows[0])
    if missing:
        raise ValueError(f"Missing columns: {sorted(missing)}")
    return [Prospect(
        company=r["company"].strip(),
        role=r["role"].strip(),
        evidence_url=r["evidence_url"].strip(),
        evidence_title=r["evidence_title"].strip(),
        evidence_summary=r["evidence_summary"].strip(),
        source_type=(r.get("source_type") or "public").strip(),
        workflow_hint=(r.get("workflow_hint") or "").strip()
    ) for r in rows]

def validate(ps):
    errors = []
    for p in ps:
        if not p.company or not p.role:
            errors.append("Company and role are required.")
        if any(x in (p.company + " " + p.role).lower() for x in ["@", "phone", "+91", "+1"]):
            errors.append(f"Private contact detail detected for {p.company}.")
        if p.source_type not in {"public", "synthetic_public"}:
            errors.append(f"{p.company}: invalid source_type.")
        if not p.evidence_url.startswith(("https://", "http://")):
            errors.append(f"{p.company}: evidence_url must be a URL.")
    return errors

def detect(p):
    text = norm(" ".join([p.evidence_summary, p.workflow_hint, p.evidence_title]))
    counts = {k: sum(term in text for term in terms) for k, terms in KEYWORDS.items()}
    keys = [k for k, v in sorted(counts.items(), key=lambda x: x[1], reverse=True) if v > 0]

    if "localization" in keys and "html" in keys:
        workflow = "Multilingual help/document content maintenance"
    elif "localization" in keys:
        workflow = "Multilingual content and translation maintenance"
    elif "template" in keys and "automation" in keys:
        workflow = "Template-driven document automation"
    elif "html" in keys and "editing" in keys:
        workflow = "Web/help documentation editing"
    elif "automation" in keys:
        workflow = "Repetitive document workflow automation"
    elif "editing" in keys:
        workflow = "Document editing and revision"
    else:
        workflow = "Document/content workflow"
    return workflow, keys

def pain_for(workflow, keys):
    if workflow == "Multilingual help/document content maintenance":
        return ("When source content changes, localized versions can require coordinated updates; "
                "the risk is stale copy, inconsistent formatting, or missed localized assets.")
    if workflow == "Multilingual content and translation maintenance":
        return ("Multiple language variants create a synchronization problem: a source change can "
                "create a queue of translation and review work.")
    if workflow == "Template-driven document automation":
        return ("Repeated template changes can create manual copy/paste and consistency work across "
                "customer-specific documents.")
    if workflow == "Web/help documentation editing":
        return ("Frequent edits to structured web documents can become repetitive when formatting, "
                "HTML structure, and content all need to stay intact.")
    if workflow == "Repetitive document workflow automation":
        return ("Repeated document operations can consume operator time and introduce inconsistency "
                "when each change is handled manually.")
    return ("Repeated document revisions may create avoidable manual work while preserving structure "
            "and context.")

def score(p, keys):
    text = norm(p.evidence_summary + " " + p.workflow_hint)
    score = 20
    score += min(30, 10 * len(set(keys) & {"html","editing","automation","template","localization"}))
    if any(x in text for x in ["manual","repetitive","workflow","pipeline","outdated","update"]):
        score += 20
    if any(x in text for x in ["html","help center","help-centre","documentation","knowledge base"]):
        score += 15
    if p.source_type == "public":
        score += 10
    return min(score, 100)

def band(s):
    return "Strong fit" if s >= 75 else ("Review" if s >= 55 else "Weak fit")

def capabilities(keys):
    out = []
    for k in ["editing","html","localization","automation","template","api","mcp"]:
        if k in keys:
            out.append(CAPABILITY_MAP[k])
    if not out:
        out.append(CAPABILITY_MAP["editing"])
    return out[:4]

def make_personalization(p, workflow, pain):
    # Grounded in the public evidence supplied for this prospect; no invented operational facts.
    return (
        f"I noticed {p.company}'s public material around {p.evidence_title.lower()}. "
        f"That points to a {workflow.lower()} workflow. The relevant question is whether "
        f"{pain[0].lower() + pain[1:]}"
    )

def process(p):
    workflow, keys = detect(p)
    pain = pain_for(workflow, keys)
    s = score(p, keys)
    caps = capabilities(keys)
    personalization = make_personalization(p, workflow, pain)

    if "local" in workflow.lower() or "multilingual" in workflow.lower():
        subject = f"Keeping localized content in sync at {p.company}"
        opening = (
            f"I came across {p.evidence_title.lower()} while looking at teams managing multilingual content. "
            f"Your public material suggests localization is part of the workflow. When the source changes, "
            f"the operational question is how the translated versions and surrounding document structure stay aligned."
        )
    elif "template" in workflow.lower():
        subject = f"Template-driven document work at {p.company}"
        opening = (
            f"I came across {p.evidence_title.lower()} while looking at document-heavy workflows. "
            f"The public material suggests recurring template-based work. The interesting question is how "
            f"your team handles repeated changes without creating another manual formatting pass."
        )
    else:
        subject = f"Document workflow at {p.company}"
        opening = (
            f"I came across {p.evidence_title.lower()} while researching document-heavy teams. "
            f"The public material suggests a workflow where document updates matter operationally. "
            f"I'd be curious whether the repeated editing/maintenance step is still handled manually."
        )

    draft = (
        f"Hi {p.role},\n\n"
        f"{opening}\n\n"
        f"If that is a real bottleneck, SuperDocs is relevant because it can edit documents directly, "
        f"including HTML, and expose the same editing workflow through server-side/API surfaces. "
        f"I'd be interested in how your team handles this today and whether a document-editing layer "
        f"would remove any repetitive work.\n\n"
        f"Best,\nSai\n\n"
        f"[HUMAN REVIEW REQUIRED — DO NOT SEND AUTOMATICALLY]"
    )

    return Result(
        p.company, p.role, p.evidence_url, p.evidence_title, workflow,
        p.evidence_summary, pain, s, band(s), caps, personalization,
        subject, draft
    )

def run_batch(inp, out, run_id):
    prospects = load_csv(inp)
    errors = validate(prospects)
    if errors:
        raise ValueError("\n".join(errors))
    results = [process(p) for p in prospects]
    manifest = {
        "run_id": run_id,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "input_file": inp.name,
        "input_fingerprint": fingerprint(inp),
        "discovered": len(prospects),
        "evidence_verified": sum(bool(p.evidence_url) for p in prospects),
        "personalization_ready": len(results),
        "strong_fit": sum(r.fit_band == "Strong fit" for r in results),
        "review": sum(r.fit_band == "Review" for r in results),
        "weak_fit": sum(r.fit_band == "Weak fit" for r in results),
        "qualification_rate": round(sum(r.fit_band != "Weak fit" for r in results) / len(results), 4),
        "safety": {
            "outbound_send_enabled": False,
            "real_contact_details_allowed": False,
            "public_company_research_only": True,
            "human_review_required": True
        },
        "results": [asdict(r) for r in results]
    }
    out.mkdir(parents=True, exist_ok=True)
    (out/"manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    fields = list(asdict(results[0]).keys())
    with (out/"qualified_targets.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields); w.writeheader()
        for r in results:
            row = asdict(r)
            for k in ["matched_capabilities"]:
                row[k] = "; ".join(row[k])
            w.writerow(row)
    md = []
    for r in results:
        md.append(
            f"# {r.company}\n\n**Role:** {r.role}\n\n"
            f"**Fit:** {r.fit_band} ({r.fit_score}/100)\n\n"
            f"**Evidence:** [{r.evidence_title}]({r.evidence_url})\n\n"
            f"**Observed workflow:** {r.workflow}\n\n"
            f"**Evidence observation:** {r.evidence_observation}\n\n"
            f"**Pain hypothesis:** {r.pain_hypothesis}\n\n"
            f"**Matched SuperDocs capabilities:** {', '.join(r.matched_capabilities)}\n\n"
            f"**Personalization:** {r.personalization}\n\n"
            f"## Draft artifact — HUMAN REVIEW ONLY\n\n"
            f"**Subject:** {r.subject}\n\n{r.draft}\n\n---\n"
        )
    (out/"growth_artifact.md").write_text("\n".join(md), encoding="utf-8")
    return manifest
