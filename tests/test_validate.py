"""Unit tests for the deterministic reconciliation layer.

These tests run with NO network and NO API key. They import directly from
src.validate and src.schema; because src/__init__.py is empty, importing here
never pulls in src.extract or the anthropic package.
"""

from src.schema import Invoice, LineItem
from src.validate import Finding, trust_score, validate


def make_clean_invoice() -> Invoice:
    """Build a fully reconciling invoice.

    Lines: 10*24.90=249.00, 4*38.00=152.00, 2*65.50=131.00 -> subtotal 532.00.
    532.00 - 0 discount + 90.44 tax = 622.44 total.
    """

    return Invoice(
        vendor_name="ACME Office Supplies Ltd",
        invoice_number="INV-2024-0417",
        invoice_date="2024-03-14",
        due_date="2024-04-13",
        currency="ILS",
        subtotal=532.00,
        tax=90.44,
        discount=None,
        total=622.44,
        line_items=[
            LineItem(description="A4 Paper", quantity=10, unit_price=24.90, amount=249.00),
            LineItem(description="Ballpoint Pens", quantity=4, unit_price=38.00, amount=152.00),
            LineItem(description="Stapler", quantity=2, unit_price=65.50, amount=131.00),
        ],
        field_confidence={"total": "high"},
        extraction_warnings=[],
    )


def _errors(findings: list[Finding]) -> list[Finding]:
    return [f for f in findings if f.severity == "error"]


def _warnings(findings: list[Finding]) -> list[Finding]:
    return [f for f in findings if f.severity == "warning"]


def test_clean_invoice_has_no_errors_and_high_score():
    findings = validate(make_clean_invoice())
    assert _errors(findings) == []
    assert trust_score(findings) >= 85


def test_wrong_total_raises_total_error():
    inv = make_clean_invoice()
    inv.total = 999.99
    findings = validate(inv)
    errors = _errors(findings)
    assert any(f.field == "total" for f in errors)


def test_wrong_line_amount_raises_line_error():
    inv = make_clean_invoice()
    inv.line_items[0].amount = 300.00  # 10 * 24.90 = 249.00, not 300.00
    findings = validate(inv)
    errors = _errors(findings)
    assert any(f.field.startswith("line_items[0]") for f in errors)


def test_missing_vendor_name_raises_required_error():
    inv = make_clean_invoice()
    inv.vendor_name = None
    findings = validate(inv)
    errors = _errors(findings)
    assert any(f.field == "vendor_name" for f in errors)


def test_unparseable_date_raises_warning():
    inv = make_clean_invoice()
    inv.invoice_date = "not a date at all"
    findings = validate(inv)
    warnings = _warnings(findings)
    assert any(f.field == "invoice_date" for f in warnings)


def test_low_field_confidence_raises_warning():
    inv = make_clean_invoice()
    inv.field_confidence = {"total": "low"}
    findings = validate(inv)
    warnings = _warnings(findings)
    assert any(f.field == "total" for f in warnings)


def test_trust_score_floors_at_zero():
    errors = [Finding(f"f{i}", "error", "boom") for i in range(10)]
    assert trust_score(errors) == 0
