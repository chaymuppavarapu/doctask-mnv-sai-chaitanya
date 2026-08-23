
from pathlib import Path
import json
import streamlit as st
from engine import run_batch

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
RUNS = ROOT / "runs"

st.set_page_config(page_title="SuperDocs Growth Machine", page_icon="🎯", layout="wide")
st.title("🎯 SuperDocs Growth Machine")
st.caption("Research → qualify → evidence → personalize → human review. No outreach is sent.")

with st.sidebar:
    st.header("Safety contract")
    st.success("OUTBOUND SENDING: DISABLED")
    st.write("Public company research only. Companies and roles are allowed; private people/contact details are not.")
    st.warning("Every generated artifact requires human review.")
    st.divider()
    st.write("**Channel:** outbound research + personalization")
    st.write("**Audience:** B2B SaaS teams with document-heavy workflows")

run_tab, evidence_tab, method_tab = st.tabs(["Run machine", "Two-run evidence", "Methodology"])

with run_tab:
    files = sorted(DATA.glob("batch_*.csv"))
    selected = st.selectbox("Input batch", [p.name for p in files])
    upload = st.file_uploader("Optional fresh CSV", type="csv")
    st.caption("Columns: company, role, evidence_url, evidence_title, evidence_summary. Optional: source_type, workflow_hint.")
    if st.button("Run machine", type="primary", use_container_width=True):
        if upload:
            inp = DATA / "uploaded_fresh_batch.csv"
            inp.write_bytes(upload.getvalue())
        else:
            inp = DATA / selected
        existing = sorted(RUNS.glob("run_*"))
        run_no = len(existing) + 1
        rid = f"run_{run_no:03d}"
        try:
            m = run_batch(inp, RUNS / rid, rid)
            st.session_state["last"] = m
            st.success(f"{rid} completed.")
        except Exception as e:
            st.error(str(e))

    if "last" in st.session_state:
        m = st.session_state["last"]
        cols = st.columns(5)
        cols[0].metric("Discovered", m["discovered"])
        cols[1].metric("Evidence", m["evidence_verified"])
        cols[2].metric("Strong", m["strong_fit"])
        cols[3].metric("Review", m["review"])
        cols[4].metric("Qualified", f'{m["qualification_rate"]:.0%}')
        st.subheader("Machine-produced growth artifact")
        for r in m["results"]:
            with st.expander(f'{r["company"]} · {r["fit_band"]} · {r["fit_score"]}/100'):
                st.write(f'**Role:** {r["role"]}')
                st.write(f'**Evidence:** {r["evidence_title"]}')
                st.write(r["evidence_url"])
                st.write(f'**Observed workflow:** {r["workflow"]}')
                st.write(f'**Pain hypothesis:** {r["pain_hypothesis"]}')
                st.write(f'**Capabilities:** {", ".join(r["matched_capabilities"])}')
                st.markdown("**Personalization**")
                st.write(r["personalization"])
                st.markdown("**Draft — HUMAN REVIEW ONLY**")
                st.code(r["draft"])

with evidence_tab:
    st.subheader("Fresh-batch repeatability")
    st.write("The same machine is run on two distinct batches without a code change between runs.")
    manifests = []
    for p in sorted(RUNS.glob("run_*")):
        f = p / "manifest.json"
        if f.exists():
            m = json.loads(f.read_text())
            manifests.append(m)
            cols = st.columns(5)
            cols[0].metric(m["run_id"], m["discovered"])
            cols[1].metric("Evidence", m["evidence_verified"])
            cols[2].metric("Strong", m["strong_fit"])
            cols[3].metric("Review", m["review"])
            cols[4].metric("Qualified", f'{m["qualification_rate"]:.0%}')
            st.caption(f'{m["input_file"]} · fingerprint {m["input_fingerprint"]}')
    if len(manifests) >= 2:
        st.success("Two-run evidence exists and the input fingerprints are different.")

with method_tab:
    st.subheader("Methodology and boundaries")
    st.markdown("""
### Audience
B2B SaaS teams with document-heavy workflows where public evidence shows recurring editing, HTML/help content, templates, localization, or document automation.

### Machine
Discover/ingest public evidence → validate → infer workflow → form a pain hypothesis → map only supported SuperDocs capabilities → personalize → produce a human-review artifact → measure.

### Measurement
Discovery count, evidence coverage, qualification rate, fit bands, input fingerprint, and timestamp.

### Leakage
Weak public evidence, generic signals, false-positive workflow inference, and personalization that overstates what the evidence proves.

### 10× risks
Evidence freshness, duplicate company normalization, source quality, and human-review capacity.

### Human loop
A human verifies evidence, approves fit, checks claims, and decides whether any real-world outreach should happen. This app cannot send outreach.
""")
