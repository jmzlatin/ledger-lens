# 🧾 Ledger Lens

**The LLM extracts. Deterministic code reconciles.**

Ledger Lens ingests a *messy* invoice — bad OCR, odd layout, inconsistent
labels — and turns it into clean structured data. The point isn't just the
extraction. The point is the **deterministic validation layer** that
independently re-checks the model's output by reconciling the arithmetic.

## Why this matters (the FDE framing)

An LLM is a great *perceiver* and a poor *calculator*. Asking a model to both
read an invoice **and** vouch that the numbers add up couples two failure modes:
you can never tell whether a "correct" total was transcribed or hallucinated.
Ledger Lens keeps the jobs separate. The model transcribes every number
**exactly as printed** — even when the invoice doesn't add up — and is *never*
asked to correct, round, or reconcile anything. A separate, non-LLM layer
(`src/validate.py`) is the **sole authority** on whether the math is valid. That
separation is what makes the output *trustworthy*: the green/red panel you see
was produced by code you can read, not by a model you have to trust.

## 5-minute quickstart

```bash
# 1. Install
pip install -r requirements.txt

# 2. Add your key
cp .env.example .env       # then paste your ANTHROPIC_API_KEY into .env

# 3. Run the demo
streamlit run app.py

# 4. Run the deterministic tests (no API key needed)
pytest
```

In the app: pick a sample invoice from the sidebar (or paste your own), click
**Extract & validate**, and read the two panels — extracted fields on the left,
the trust score and reconciliation findings on the right.

## How it works

```
   raw invoice text
        │
        ▼
  src/extract.py    Claude, forced tool use  →  structured Invoice (numbers as printed)
        │
        ▼
  src/validate.py   pure Python, NO LLM       →  findings + trust score
        │
        ▼
  app.py            Streamlit                 →  fields + red/green reconciliation panel
```

- **`src/schema.py`** — Pydantic v2 `Invoice` / `LineItem`. Every scalar field
  is optional; a missing or illegible value is `null`, never invented.
- **`src/extract.py`** — one forced-tool-use call (`record_invoice`) so the
  model must return structured JSON, not prose. The system prompt enforces the
  thesis: transcribe as printed, never reconcile, `null` for missing, honest
  `field_confidence`, and every ambiguity logged to `extraction_warnings`.
- **`src/validate.py`** — the core. Pure, deterministic Python with **no LLM
  imports**. It re-derives the math with a money tolerance (1¢ or 0.5%) and
  emits `Finding`s, then a `trust_score` (start 100; −25 per error, −8 per
  warning).

What the validator checks:
1. Required fields present (`vendor_name`, `invoice_number`, `total`).
2. Per line: `quantity × unit_price ≈ amount`.
3. `sum(line amounts) ≈ subtotal`.
4. `subtotal − discount + tax ≈ total`.
5. Dates parse, and `due_date ≥ invoice_date`.
6. Any field the model marked low-confidence.
7. Every extraction warning the model logged.

## The sample invoices

`samples/` holds eight fake invoices that exercise the pipeline. Clean ones
reconcile; the "broken" ones are *supposed* to fail, and that failing is the
demo:

| Sample | What it shows |
|---|---|
| `invoice_clean_ils.txt` | Tidy invoice, everything reconciles. |
| `invoice_usd_simple.txt` | Minimal single-line invoice. |
| `invoice_multi_eur.txt` | Multi-line with a discount line. |
| `invoice_weird_labels.txt` | Non-standard labels ("Net amount", "Amount payable"). |
| `invoice_broken_total.txt` | Subtotal + tax ≠ printed total → **total error**. |
| `invoice_line_mismatch.txt` | A line's `qty × rate ≠ amount` → **line error**. |
| `invoice_missing_fields.txt` | No invoice number → **required-field error**. |
| `invoice_ocr_noise.txt` | OCR artifacts; a smudged VAT figure stays `null`. |

## Example reconciliation output

The deterministic layer run against the sample numbers (this is `validate` +
`trust_score`, no model involved):

```
clean_ils      score=100  errors=0  →  All checks passed; invoice reconciles.
multi_eur      score=100  errors=0  →  All checks passed; invoice reconciles.
broken_total   score= 67  errors=1  →  [error] total: Total 6540.00 ≠ subtotal 5940.00 + tax 924.80 (= 6864.80)
line_mismatch  score= 75  errors=1  →  [error] line_items[0]: amount 4200.00 ≠ 3 × 1500.00 (= 4500.00)
missing_fields score= 75  errors=1  →  [error] invoice_number: required field is missing
ocr_noise      score= 51  errors=1  →  [error] total: tax was illegible (null) so the total can't be confirmed
```

## Screenshot

> _Placeholder — drop a capture of the two-panel result view at
> `docs/screenshot.png` after your first run (it needs an API key to populate
> the panels), and it will render here:_

<!-- ![Ledger Lens trust panel](docs/screenshot.png) -->

## Notes

- Money comparisons use a tolerance (1¢ or 0.5%), never exact float `==`.
- Tests import the validator directly and run with **no API key** and even with
  `anthropic` not installed — proof that the reconciliation layer is fully
  independent of the model.
- Default model is `claude-sonnet-4-6`, kept in one place (`DEFAULT_MODEL`) so
  it's swappable.

## Scope

This is an intentionally small MVP. PDF/image input, editable results, audit
logging, and an eval harness are deliberately deferred (see `PLAN.md`).
