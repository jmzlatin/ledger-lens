# CLAUDE.md — Invoice Extractor (MVP)

Persistent context for Claude Code. Read this before every task.

## What this project is
A Forward-Deployed-Engineer-style demo. It ingests a **messy invoice** (bad OCR,
odd layout, inconsistent labels) and turns it into **clean structured data**.

The whole point — the thing that makes it portfolio-worthy — is a
**deterministic validation layer** that independently re-checks the model's
output by reconciling the arithmetic.

## Core thesis (NON-NEGOTIABLE)
**The LLM extracts. Deterministic code reconciles.**
- The model transcribes numbers *exactly as printed*, even when they don't add up.
- The model is NEVER asked to correct, round, or reconcile anything.
- A separate, non-LLM layer is the *sole authority* on whether the math is valid.
- `src/validate.py` must not import or call anthropic / any LLM.

Keeping these two concerns separate is the demo. Do not blur them.

## Stack
- Python 3.11+
- Streamlit (frontend)
- `anthropic` (Python SDK)
- Pydantic v2 (schema + parsing)
- pytest (tests the deterministic layer — runs with no API key)

## Models
- Default extraction model constant `DEFAULT_MODEL = "claude-sonnet-4-6"`
  (fast + accurate for structured perception; cheap to iterate on).
- Keep the model name in ONE place so it's swappable.

## Extraction must use forced tool use
Call the API with a single tool and `tool_choice={"type": "tool", "name": ...}`
so the model is forced to return a structured JSON object, not prose. Read the
result from the `tool_use` content block. Do not regex/parse free text.

## Conventions
- Missing or illegible value → `null`. Never invent a value to fill a gap.
- Secrets via `.env` (`ANTHROPIC_API_KEY`). Never hard-code a key.
- Small, pure functions. The validator signature is `validate(invoice) -> list[Finding]`.
- Money comparisons use a tolerance (1 cent or 0.5%), never exact `==` on floats.
- Keep `src/__init__.py` EMPTY. If it imports `extract`, then importing `schema`
  or `validate` transitively pulls in the anthropic SDK — which breaks the rule
  that the validator and its tests run with no API key (and even with anthropic
  not installed). Tests import directly: `from src.validate import ...`.

## Target structure
```
app.py                 # Streamlit entrypoint (keep minimal)
src/__init__.py
src/schema.py          # Pydantic Invoice / LineItem
src/extract.py         # Claude forced tool-use extraction
src/validate.py        # deterministic reconciliation -> findings (NO LLM)
samples/*.txt          # fake invoices (already provided)
tests/test_validate.py # unit tests, no network
requirements.txt
.env.example
```

## How to run
```
pip install -r requirements.txt
cp .env.example .env      # then paste your key
streamlit run app.py
pytest                    # deterministic layer only
```

## MVP scope guardrail
Build the SMALLEST thing that demonstrates the thesis:
paste/select invoice → extract → show fields + reconciliation findings.
**Out of scope for MVP** (do NOT build yet): PDF/image parsing, auth, a database,
logging, batch upload, custom styling, confidence tuning. These live in
PLAN.md → "Later". If a task isn't in tasks.md, don't build it.
