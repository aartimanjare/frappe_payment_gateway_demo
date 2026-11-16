"""Provider reply normalization (no Frappe or network needed)."""

import unittest
from decimal import Decimal

from frappe_payment_gateway_demo.payment_gateway_demo.gateway.client import (
	from_minor_units,
	normalize_result,
	normalize_status,
)


class TestNormalize(unittest.TestCase):
	"""normalize_status(), from_minor_units(), normalize_result()."""

	def test_statuses_map_to_three_states(self):
		"""Provider wording maps to Success / Failed; anything unknown stays Pending."""
		self.assertEqual(normalize_status("success"), "Success")
		self.assertEqual(normalize_status(" Paid "), "Success")
		self.assertEqual(normalize_status("abandoned"), "Failed")
		self.assertEqual(normalize_status("ongoing"), "Pending")
		self.assertEqual(normalize_status(None), "Pending")

	def test_minor_units_become_major_units(self):
		"""150050 kobo/cents is 1500.50."""
		self.assertEqual(from_minor_units(150050), Decimal("1500.50"))
		self.assertEqual(from_minor_units("99"), Decimal("0.99"))

	def test_result_shape(self):
		"""A provider object becomes the app's common shape."""
		self.assertEqual(
			normalize_result({"reference": "abc", "status": "success", "amount": 2500, "currency": "ngn"}),
			{"reference": "abc", "status": "Success", "amount": Decimal("25.00"), "currency": "NGN"},
		)


if __name__ == "__main__":
	unittest.main()
