"""Ledger Lens — Streamlit entrypoint.

The LLM extracts numbers exactly as printed; deterministic code reconciles
the arithmetic. This file is intentionally minimal (see CLAUDE.md scope).
"""

import streamlit as st

st.set_page_config(page_title="Ledger Lens", page_icon="🧾")

st.title("🧾 Ledger Lens")
st.caption("The LLM extracts. Deterministic code reconciles.")
