"""Webhook signature checks (no Frappe needed)."""

import unittest

from frappe_payment_gateway_demo.payment_gateway_demo.gateway.signature import (
	compute_signature,
	is_valid_signature,
)

SECRET = "whsec_test"
BODY = b'{"event":"charge.success","data":{"reference":"abc","amount":150050,"currency":"NGN"}}'


class TestSignature(unittest.TestCase):
	"""is_valid_signature()."""

	def test_valid_signature_is_accepted(self):
		"""The provider's own digest passes, in either letter case."""
		signature = compute_signature(BODY, SECRET)
		self.assertTrue(is_valid_signature(BODY, signature, SECRET))
		self.assertTrue(is_valid_signature(BODY, signature.upper(), SECRET))

	def test_tampered_body_is_rejected(self):
		"""Changing one byte of the body breaks the signature."""
		signature = compute_signature(BODY, SECRET)
		self.assertFalse(is_valid_signature(BODY.replace(b"150050", b"950050"), signature, SECRET))

	def test_wrong_secret_is_rejected(self):
		"""A digest made with another secret fails."""
		self.assertFalse(is_valid_signature(BODY, compute_signature(BODY, "other"), SECRET))

	def test_missing_parts_are_rejected(self):
		"""No signature, no secret or no body never counts as valid."""
		signature = compute_signature(BODY, SECRET)
		self.assertFalse(is_valid_signature(BODY, None, SECRET))
		self.assertFalse(is_valid_signature(BODY, signature, None))
		self.assertFalse(is_valid_signature(b"", signature, SECRET))


if __name__ == "__main__":
	unittest.main()
