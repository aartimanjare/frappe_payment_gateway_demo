"""Split one payment across several open invoices.

Pure functions: the oldest invoice (by due date) is paid first, money is kept
as Decimal so rounding never creates or loses a paisa/cent.
"""

from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal


@dataclass(frozen=True)
class OpenInvoice:
	"""An invoice that can receive part of a payment."""

	name: str
	due_date: str  # ISO date, e.g. "2026-11-30"
	outstanding: Decimal


def to_money(value) -> Decimal:
	"""
	Convert a number to a 2-decimal Decimal.

	Parameters:
		value (int | float | str | Decimal, required): The amount.

	Returns:
		Decimal: The amount rounded half-up to 2 places.
	"""
	return Decimal(str(value)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def allocate(amount, invoices: list[OpenInvoice]) -> list[tuple[str, Decimal]]:
	"""
	Allocate a payment to invoices, oldest due date first.

	Parameters:
		amount (int | float | str | Decimal, required): The amount paid.
		invoices (list[OpenInvoice], required): Invoices the payment may settle.

	Returns:
		list[tuple[str, Decimal]]: (invoice name, allocated amount) in allocation order.

	Raises:
		ValueError: When the amount is not positive or exceeds the total outstanding.
	"""
	amount = to_money(amount)
	if amount <= 0:
		raise ValueError("Payment amount must be greater than zero")

	total_outstanding = sum((to_money(invoice.outstanding) for invoice in invoices), Decimal("0"))
	if amount > total_outstanding:
		raise ValueError(f"Payment {amount} is more than the total outstanding {total_outstanding}")

	allocations = []
	remaining = amount
	for invoice in sorted(invoices, key=lambda invoice: (invoice.due_date, invoice.name)):
		if remaining == 0:
			break
		share = min(remaining, to_money(invoice.outstanding))
		if share > 0:
			allocations.append((invoice.name, share))
			remaining -= share
	return allocations
