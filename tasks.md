# tasks.md — MVP Build

Work top to bottom. Check off each task only when its **Done when** is satisfied.
Keep everything minimal — if it isn't listed here, don't build it (see CLAUDE.md
scope guardrail).

---

## Phase 0 — Setup

- [ ] **0.1 Dependencies & env**
  - Ensure `requirements.txt`, `.env.example`, `.gitignore` exist (they're provided).
  - Create a venv, `pip install -r requirements.txt`.
  - Create `src/__init__.py` and a `tests/` folder.
  - **Done when** `python -c "import streamlit, anthropic, pydantic"` succeeds.

- [ ] **0.2 Blank app**
  - Create `app.py` with a title and one line of caption.
  - **Done when** `streamlit run app.py` opens a page with the title.

---

## Phase 1 — Backend core

- [ ] **1.1 Schema** (`src/schema.py`)
  - Pydantic v2 models `LineItem` (description, quantity, unit_price, amount —
    all optional except description) and `Invoice` (vendor_name, invoice_number,
    invoice_date, due_date, currency, line_items, subtotal, tax, discount, total,
    plus `field_confidence: dict[str,str]` and `extraction_warnings: list[str]`).
  - All scalar fields Optional; default `null`.
  - **Done when** `Invoice(line_items=[])` constructs without error.

- [ ] **1.2 Extraction** (`src/extract.py`)
  - One tool definition `record_invoice` whose input_schema mirrors the Invoice.
  - `extract_invoice(raw_text, client=None, model=DEFAULT_MODEL) -> Invoice`.
  - Use `tool_choice={"type":"tool","name":"record_invoice"}` (forced).
  - System prompt enforces the thesis: transcribe numbers EXACTLY as printed,
    never reconcile; `null` for missing; honest `field_confidence`; log ambiguity
    to `extraction_warnings`.
  - Read the `tool_use` block, `Invoice.model_validate(block.input)`.
  - `DEFAULT_MODEL = "claude-sonnet-4-6"`. Key from env via `get_client()`.
  - **Done when** running it on `samples/invoice_clean_ils.txt` returns a populated Invoice.

- [ ] **1.3 Validation** (`src/validate.py`) — *the core deliverable*
  - `@dataclass Finding(field, severity, message)` where severity ∈ {error,warning,ok}.
  - `validate(inv) -> list[Finding]` checking, with a money tolerance (1¢ or 0.5%):
    1. required fields present: vendor_name, invoice_number, total
    2. each line: `quantity * unit_price ≈ amount` (when all three present)
    3. `sum(line amounts) ≈ subtotal`
    4. `subtotal - discount + tax ≈ total`
    5. dates parseable; due_date ≥ invoice_date (warnings)
    6. any `field_confidence == "low"` → warning
    7. each `extraction_warnings` entry → warning
  - `trust_score(findings) -> int` (start 100; −25 per error, −8 per warning; floor 0).
  - **NO LLM imports in this file.**
  - **Done when** Task 1.4 tests pass.

- [ ] **1.4 Tests** (`tests/test_validate.py`)
  - Build a known-reconciling Invoice in code; assert no errors, score ≥ 85.
  - Mutate it to break: wrong total → total error; wrong line amount → line error;
    drop vendor_name → required error; bad date → warning; set a low confidence → warning.
  - **Done when** `pytest` is green (no network needed).

---

## Phase 2 — Minimal frontend

- [ ] **2.1 Wire the UI** (`app.py`)
  - Sidebar: show whether `ANTHROPIC_API_KEY` is set; a `selectbox` listing
    `samples/*.txt`.
  - Main: a `text_area` prefilled from the chosen sample; an **Extract & validate** button.
  - On click: `extract_invoice` → `validate` → `trust_score`.
  - Two columns: left = extracted fields (a table) + line-items table + a
    "Download JSON" button; right = trust score + findings grouped error/warning/ok
    (use `st.error` / `st.warning` / `st.success`).
  - Wrap the API call in try/except and surface failures in the UI.
  - **Done when** selecting a sample and clicking the button shows both panels.

---

## Phase 3 — Smoke test & README

- [ ] **3.1 Manual smoke test**
  - Run all 8 samples. Confirm: clean ones reconcile (high score, no errors);
    `invoice_broken_total` and `invoice_line_mismatch` raise the right errors;
    `invoice_missing_fields` flags the missing required field.
  - Fix any mismatch between expected and actual behavior.
  - **Done when** every sample behaves as its name implies.

- [ ] **3.2 README**
  - 5-minute quickstart (install, env, run) + the one-paragraph "why this matters"
    FDE framing (LLM perceives, code verifies) + a screenshot.
  - **Done when** the README alone gets a new user to a working demo.

---

## MVP exit criteria
`pytest` green · all 8 samples behave correctly · a non-technical viewer can
watch one extraction and understand what the trust panel is telling them.
Then we write the improvement tasks (PLAN.md → "Later").
