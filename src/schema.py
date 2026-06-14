"""Pydantic v2 models for an extracted invoice.

These models hold numbers EXACTLY as transcribed from the source document.
They perform no reconciliation, rounding, or correction — that is the sole
job of src/validate.py. Every scalar field is optional and defaults to None
so that a missing or illegible value is represented as null, never invented.
"""

from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field


class LineItem(BaseModel):
    """A single line on the invoice, transcribed as printed."""

    description: str
    quantity: Optional[float] = None
    unit_price: Optional[float] = None
    amount: Optional[float] = None


class Invoice(BaseModel):
    """A whole invoice, transcribed as printed.

    `field_confidence` maps a field name to a confidence label (e.g. "low")
    and `extraction_warnings` collects any ambiguity noticed during
    extraction. Neither influences the numbers themselves.
    """

    vendor_name: Optional[str] = None
    invoice_number: Optional[str] = None
    invoice_date: Optional[str] = None
    due_date: Optional[str] = None
    currency: Optional[str] = None
    subtotal: Optional[float] = None
    tax: Optional[float] = None
    discount: Optional[float] = None
    total: Optional[float] = None
    line_items: list[LineItem] = Field(default_factory=list)
    field_confidence: dict[str, str] = Field(default_factory=dict)
    extraction_warnings: list[str] = Field(default_factory=list)
