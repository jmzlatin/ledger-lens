"""Deterministic reconciliation layer — the core of this project.

This module is the SOLE authority on whether an invoice's arithmetic is
internally consistent. It independently re-checks the numbers the LLM
transcribed; it never trusts the model to have reconciled anything.

NON-NEGOTIABLE: this file MUST NOT import or call anthropic or any LLM. It is
pure, deterministic Python and its tests run with no API key (and even with
the anthropic package not installed).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from dateutil import parser as date_parser

from src.schema import Invoice


@dataclass
class Finding:
    """A single reconciliation result.

    severity is one of: "error", "warning", "ok".
    """

    field: str
    severity: str
    message: str


def _money_equal(a: float, b: float) -> bool:
    """Compare two money amounts with tolerance (1 cent or 0.5%).

    Never use exact == on floats. Equal if the absolute difference is within
    the larger of 1 cent and 0.5% of the larger magnitude.
    """

    tolerance = max(0.01, 0.005 * max(abs(a), abs(b)))
    return abs(a - b) <= tolerance


def _parse_date(value: str):
    """Parse a date string, returning a datetime or None if unparseable."""

    try:
        return date_parser.parse(value)
    except (ValueError, OverflowError, TypeError):
        return None


def validate(inv: Invoice) -> list[Finding]:
    """Reconcile an invoice's arithmetic and return findings.

    Checks (in order):
      1. required fields present: vendor_name, invoice_number, total
      2. each line: quantity * unit_price ~= amount (when all three present)
      3. sum(line amounts) ~= subtotal
      4. subtotal - discount + tax ~= total
      5. dates parseable; due_date >= invoice_date
      6. any field_confidence value == "low"
      7. each extraction_warnings entry

    If no findings are produced, returns a single "ok" finding.
    """

    findings: list[Finding] = []

    # 1. Required fields present.
    required = {
        "vendor_name": inv.vendor_name,
        "invoice_number": inv.invoice_number,
        "total": inv.total,
    }
    for field, value in required.items():
        if value is None:
            findings.append(
                Finding(field, "error", f"Required field '{field}' is missing.")
            )

    # 2. Per-line: quantity * unit_price ~= amount (only when all present).
    for idx, line in enumerate(inv.line_items):
        if (
            line.quantity is not None
            and line.unit_price is not None
            and line.amount is not None
        ):
            expected = line.quantity * line.unit_price
            if not _money_equal(expected, line.amount):
                findings.append(
                    Finding(
                        f"line_items[{idx}].amount",
                        "error",
                        (
                            f"Line {idx} amount {line.amount} does not match "
                            f"quantity * unit_price = {line.quantity} * "
                            f"{line.unit_price} = {expected}."
                        ),
                    )
                )

    # 3. Sum of line amounts ~= subtotal.
    line_amounts = [li.amount for li in inv.line_items if li.amount is not None]
    if inv.subtotal is not None and line_amounts:
        line_sum = sum(line_amounts)
        if not _money_equal(line_sum, inv.subtotal):
            findings.append(
                Finding(
                    "subtotal",
                    "error",
                    (
                        f"Subtotal {inv.subtotal} does not match the sum of "
                        f"line amounts ({line_sum})."
                    ),
                )
            )

    # 4. subtotal - discount + tax ~= total.
    if inv.subtotal is not None and inv.total is not None:
        expected_total = inv.subtotal - (inv.discount or 0) + (inv.tax or 0)
        if not _money_equal(expected_total, inv.total):
            findings.append(
                Finding(
                    "total",
                    "error",
                    (
                        f"Total {inv.total} does not match subtotal "
                        f"{inv.subtotal} - discount {inv.discount or 0} + tax "
                        f"{inv.tax or 0} = {expected_total}."
                    ),
                )
            )

    # 5. Dates parseable; due_date >= invoice_date.
    parsed_dates: dict[str, Optional[object]] = {}
    for field in ("invoice_date", "due_date"):
        raw = getattr(inv, field)
        if raw is not None:
            parsed = _parse_date(raw)
            parsed_dates[field] = parsed
            if parsed is None:
                findings.append(
                    Finding(
                        field,
                        "warning",
                        f"Could not parse {field} value '{raw}' as a date.",
                    )
                )

    inv_date = parsed_dates.get("invoice_date")
    due_date = parsed_dates.get("due_date")
    if inv_date is not None and due_date is not None and due_date < inv_date:
        findings.append(
            Finding(
                "due_date",
                "warning",
                (
                    f"Due date {inv.due_date} is before invoice date "
                    f"{inv.invoice_date}."
                ),
            )
        )

    # 6. Low-confidence fields flagged by extraction.
    for field, confidence in inv.field_confidence.items():
        if confidence == "low":
            findings.append(
                Finding(
                    field,
                    "warning",
                    f"Field '{field}' was extracted with low confidence.",
                )
            )

    # 7. Surface every extraction warning logged by the model.
    for warning in inv.extraction_warnings:
        findings.append(Finding("extraction", "warning", warning))

    # If nothing was flagged, the invoice reconciles cleanly.
    if not findings:
        return [Finding("invoice", "ok", "All checks passed; invoice reconciles.")]

    return findings


def trust_score(findings: list[Finding]) -> int:
    """Reduce findings to a 0-100 trust score.

    Start at 100; subtract 25 per error and 8 per warning; floor at 0.
    """

    score = 100
    for finding in findings:
        if finding.severity == "error":
            score -= 25
        elif finding.severity == "warning":
            score -= 8
    return max(0, score)
