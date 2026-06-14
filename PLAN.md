# PLAN.md — Plan of Attack

## Objective
Ship a minimal but *complete* demo that proves one idea: an LLM can extract
structured data from messy invoices, and deterministic code can independently
verify it by reconciling the arithmetic. Everything else is deferred.

## The shape of the MVP
```
   raw invoice text
        │
        ▼
  [ extract.py ]   Claude, forced tool use  → structured Invoice (numbers as printed)
        │
        ▼
  [ validate.py ]  pure Python, no LLM       → findings + trust score
        │
        ▼
  [ app.py ]       Streamlit                 → fields + red/green reconciliation panel
```

## Phases (MVP = Phases 0–3)

**Phase 0 — Setup.** Repo, dependencies, env, folders. Get a blank Streamlit
page running. *Done when* `streamlit run app.py` shows a title.

**Phase 1 — Backend core (the value).**
- `schema.py`: the `Invoice` / `LineItem` Pydantic models.
- `extract.py`: forced-tool-use call returning a validated `Invoice`.
- `validate.py`: the deterministic reconciliation (line math, subtotal, total,
  required fields) returning findings + a trust score.
- `tests/`: unit tests for `validate.py` (no API).
*Done when* `pytest` is green and a script can extract one sample end-to-end.

**Phase 2 — Minimal frontend.** Wire the three modules into Streamlit: a text
box (prefilled from a sample picker), an Extract button, and two panels —
extracted fields + reconciliation findings. Default styling only.
*Done when* you can run all 8 samples by hand and see correct red/green results.

**Phase 3 — Smoke test + README.** Run every sample, confirm the "broken" ones
flag and the "clean" ones pass, write a short README with the demo story.
*Done when* a stranger could clone, run, and understand it in 5 minutes.

## Later (NOT in this MVP — separate improvement plan)
- PDF / image input (Claude takes these natively via document/image blocks).
- Editable results + re-validate on edit.
- Supabase logging of every extraction for an audit trail.
- An eval harness: ground-truth JSON per sample, measured field accuracy.
- Confidence calibration, batch mode, export to Excel/PPTX.
- Domain swap (contracts, POs, bills of lading) to show the pattern generalizes.

We'll turn "Later" into its own tasks.md once the MVP runs.
