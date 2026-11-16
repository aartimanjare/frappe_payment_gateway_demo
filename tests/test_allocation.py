"""Payment allocation across invoices (no Frappe needed)."""

import unittest
from decimal import Decimal

from frappe_payment_gateway_demo.payment_gateway_demo.gateway.allocation import OpenInvoice, allocate

INVOICES = [
	OpenInvoice("SINV-0003", "2026-12-15", Decimal("300.00")),
	OpenInvoice("SINV-0001", "2026-11-01", Decimal("100.00")),
	OpenInvoice("SINV-0002", "2026-11-20", Decimal("250.50")),
]


class TestAllocate(unittest.TestCase):
	"""allocate()."""

	def test_full_payment_settles_everything_oldest_first(self):
		"""The full outstanding settles every invoice in due-date order."""
		self.assertEqual(
			allocate("650.50", INVOICES),
			[
				("SINV-0001", Decimal("100.00")),
				("SINV-0002", Decimal("250.50")),
				("SINV-0003", Decimal("300.00")),
			],
		)

	def test_part_payment_stops_at_the_amount(self):
		"""A part payment fills the oldest invoices and partly pays the next."""
		self.assertEqual(
			allocate(200, INVOICES),
			[("SINV-0001", Decimal("100.00")), ("SINV-0002", Decimal("100.00"))],
		)

	def test_allocations_always_add_up(self):
		"""No money is created or lost through rounding."""
		allocations = allocate(333.335, INVOICES)
		self.assertEqual(sum(share for _name, share in allocations), Decimal("333.34"))

	def test_overpayment_is_refused(self):
		"""Paying more than is outstanding raises an error."""
		with self.assertRaises(ValueError):
			allocate("650.51", INVOICES)

	def test_zero_or_negative_is_refused(self):
		"""Zero and negative amounts raise an error."""
		for amount in (0, -10):
			with self.assertRaises(ValueError):
				allocate(amount, INVOICES)


if __name__ == "__main__":
	unittest.main()
