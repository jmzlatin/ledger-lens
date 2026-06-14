"""Claude-powered invoice extraction via forced tool use.

The thesis of this project: the LLM TRANSCRIBES, it does not reconcile.
This module forces the model to emit a single structured object that mirrors
the Invoice schema, with numbers copied EXACTLY as printed — even when they
don't add up. All math-checking happens downstream in src/validate.py, which
never imports an LLM.
"""

from __future__ import annotations

import os
from typing import Optional

import anthropic

from src.schema import Invoice

DEFAULT_MODEL = "claude-sonnet-4-6"

SYSTEM_PROMPT = """You are a meticulous invoice transcriber. Your only job is \
to read the raw invoice text and record exactly what is printed.

NON-NEGOTIABLE RULES:
- Transcribe every number EXACTLY as printed. Do NOT reconcile, recompute, \
round, or "fix" anything — even if the line items, subtotal, tax, and total \
do not add up. Recording inconsistent numbers faithfully is correct behavior.
- If a value is missing, blank, or illegible, record null. NEVER guess or \
invent a value to fill a gap.
- Use field_confidence to be honest about each field you record. Mark a field \
"low" when the value is inferred, ambiguous, or read from degraded/noisy OCR; \
otherwise "high". Keys are field names (e.g. "total", "invoice_date").
- Log EVERY ambiguity, OCR artifact, unusual label, or judgment call to \
extraction_warnings as a short human-readable string.

You record the data by calling the record_invoice tool. Do not write prose."""

# input_schema mirrors the Invoice model. Scalar fields are nullable; the
# bookkeeping fields (line_items, field_confidence, extraction_warnings) are
# required so the model always reports its line items and its uncertainty.
RECORD_INVOICE_TOOL = {
    "name": "record_invoice",
    "description": (
        "Record the invoice fields transcribed EXACTLY as printed on the "
        "document. Use null for any missing or illegible value; never invent "
        "one. Do not reconcile or recompute the numbers."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "vendor_name": {"type": ["string", "null"]},
            "invoice_number": {"type": ["string", "null"]},
            "invoice_date": {
                "type": ["string", "null"],
                "description": "The invoice date, as printed.",
            },
            "due_date": {
                "type": ["string", "null"],
                "description": "The payment due date, as printed.",
            },
            "currency": {
                "type": ["string", "null"],
                "description": "Currency code or symbol, as printed.",
            },
            "subtotal": {"type": ["number", "null"]},
            "tax": {"type": ["number", "null"]},
            "discount": {"type": ["number", "null"]},
            "total": {"type": ["number", "null"]},
            "line_items": {
                "type": "array",
                "description": "Every line item, transcribed as printed.",
                "items": {
                    "type": "object",
                    "properties": {
                        "description": {"type": "string"},
                        "quantity": {"type": ["number", "null"]},
                        "unit_price": {"type": ["number", "null"]},
                        "amount": {"type": ["number", "null"]},
                    },
                    "required": ["description"],
                },
            },
            "field_confidence": {
                "type": "object",
                "description": (
                    "Map of field name -> confidence label ('high' or 'low'). "
                    "Use 'low' for inferred, ambiguous, or degraded values."
                ),
                "additionalProperties": {"type": "string"},
            },
            "extraction_warnings": {
                "type": "array",
                "description": "Short notes for every ambiguity or judgment call.",
                "items": {"type": "string"},
            },
        },
        "required": ["line_items", "field_confidence", "extraction_warnings"],
    },
}


def get_client(api_key: Optional[str] = None) -> anthropic.Anthropic:
    """Build an Anthropic client.

    Reads ANTHROPIC_API_KEY from the environment when `api_key` is not given.
    Raises a clear error if no key is available.
    """

    key = api_key or os.environ.get("ANTHROPIC_API_KEY")
    if not key:
        raise RuntimeError(
            "ANTHROPIC_API_KEY is not set. Pass api_key=... or set the "
            "ANTHROPIC_API_KEY environment variable (see .env.example)."
        )
    return anthropic.Anthropic(api_key=key)


def extract_invoice(
    raw_text: str,
    client: Optional[anthropic.Anthropic] = None,
    model: str = DEFAULT_MODEL,
) -> Invoice:
    """Extract a structured Invoice from raw invoice text via forced tool use."""

    if client is None:
        client = get_client()

    response = client.messages.create(
        model=model,
        max_tokens=2048,
        system=SYSTEM_PROMPT,
        tools=[RECORD_INVOICE_TOOL],
        tool_choice={"type": "tool", "name": "record_invoice"},
        messages=[
            {
                "role": "user",
                "content": (
                    "Transcribe this invoice exactly as printed:\n\n" + raw_text
                ),
            }
        ],
    )

    for block in response.content:
        if block.type == "tool_use" and block.name == "record_invoice":
            return Invoice.model_validate(block.input)

    raise RuntimeError(
        "Model did not return a record_invoice tool_use block as required."
    )
