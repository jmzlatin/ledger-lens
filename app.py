"""Ledger Lens — Streamlit entrypoint.

The LLM extracts numbers exactly as printed; deterministic code reconciles
the arithmetic. This file wires the three backend modules into a minimal UI:
pick/paste an invoice → extract → show fields + reconciliation findings.
"""

import os
from pathlib import Path

import streamlit as st

from src.extract import extract_invoice
from src.schema import Invoice
from src.validate import Finding, trust_score, validate

SAMPLES_DIR = Path(__file__).parent / "samples"


def _fmt(value) -> str:
    """Render a scalar field for display, showing missing values as a dash."""

    return "—" if value is None else str(value)


def _render_fields(inv: Invoice) -> None:
    """Show the extracted scalar fields as a two-column table."""

    rows = [
        {"Field": "Vendor", "Value": _fmt(inv.vendor_name)},
        {"Field": "Invoice #", "Value": _fmt(inv.invoice_number)},
        {"Field": "Invoice date", "Value": _fmt(inv.invoice_date)},
        {"Field": "Due date", "Value": _fmt(inv.due_date)},
        {"Field": "Currency", "Value": _fmt(inv.currency)},
        {"Field": "Subtotal", "Value": _fmt(inv.subtotal)},
        {"Field": "Discount", "Value": _fmt(inv.discount)},
        {"Field": "Tax", "Value": _fmt(inv.tax)},
        {"Field": "Total", "Value": _fmt(inv.total)},
    ]
    st.table(rows)


def _render_line_items(inv: Invoice) -> None:
    """Show the line items as a table, or a caption when there are none."""

    if not inv.line_items:
        st.caption("No line items extracted.")
        return
    rows = [
        {
            "Description": li.description,
            "Qty": _fmt(li.quantity),
            "Unit price": _fmt(li.unit_price),
            "Amount": _fmt(li.amount),
        }
        for li in inv.line_items
    ]
    st.table(rows)


def _render_findings(findings: list[Finding], score: int) -> None:
    """Show the trust score and findings grouped by severity."""

    st.metric("Trust score", f"{score}/100")

    errors = [f for f in findings if f.severity == "error"]
    warnings = [f for f in findings if f.severity == "warning"]
    oks = [f for f in findings if f.severity == "ok"]

    if errors:
        st.subheader(f"Errors ({len(errors)})")
        for f in errors:
            st.error(f"**{f.field}** — {f.message}")
    if warnings:
        st.subheader(f"Warnings ({len(warnings)})")
        for f in warnings:
            st.warning(f"**{f.field}** — {f.message}")
    if oks:
        for f in oks:
            st.success(f"**{f.field}** — {f.message}")


st.set_page_config(page_title="Ledger Lens", page_icon="🧾", layout="wide")

st.title("🧾 Ledger Lens")
st.caption("The LLM extracts. Deterministic code reconciles.")

# --- Sidebar: key status + sample picker -----------------------------------
with st.sidebar:
    st.header("Setup")
    if os.environ.get("ANTHROPIC_API_KEY"):
        st.success("ANTHROPIC_API_KEY is set.")
    else:
        st.warning("ANTHROPIC_API_KEY is not set. Extraction will fail until it is.")

    sample_files = sorted(SAMPLES_DIR.glob("*.txt"))
    sample_names = [p.name for p in sample_files]
    selected_name = st.selectbox(
        "Sample invoice",
        options=sample_names,
        help="Files from samples/. The text is editable below.",
    ) if sample_names else None
    if not sample_names:
        st.info("No samples found in samples/.")

# --- Main: editable invoice text + extract button --------------------------
default_text = ""
if selected_name:
    default_text = (SAMPLES_DIR / selected_name).read_text()

# Key the widget on the filename so switching samples reloads the default text
# while preserving manual edits made within a single sample.
raw_text = st.text_area(
    "Invoice text",
    value=default_text,
    height=320,
    key=f"text_{selected_name}",
)

extract_clicked = st.button("Extract & validate", type="primary")

# On click, run the pipeline and stash results in session_state so the panels
# survive the rerun triggered by the Download JSON button below.
if extract_clicked:
    st.session_state.pop("result", None)
    if not raw_text.strip():
        st.warning("Paste or select an invoice first.")
    else:
        with st.spinner("Extracting and reconciling…"):
            try:
                invoice = extract_invoice(raw_text)
                findings = validate(invoice)
                score = trust_score(findings)
                st.session_state["result"] = {
                    "invoice": invoice,
                    "findings": findings,
                    "score": score,
                }
            except Exception as exc:  # surface API/parse failures in the UI
                st.session_state["result"] = {"error": str(exc)}

# --- Render results (from session_state, independent of button reruns) ------
result = st.session_state.get("result")
if result and "error" in result:
    st.error(f"Extraction failed: {result['error']}")
elif result:
    invoice: Invoice = result["invoice"]
    left, right = st.columns(2)
    with left:
        st.subheader("Extracted fields")
        _render_fields(invoice)
        st.subheader("Line items")
        _render_line_items(invoice)
        st.download_button(
            "Download JSON",
            data=invoice.model_dump_json(indent=2),
            file_name=f"{invoice.invoice_number or 'invoice'}.json",
            mime="application/json",
        )
    with right:
        st.subheader("Reconciliation")
        _render_findings(result["findings"], result["score"])
