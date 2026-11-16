"""Talk to the payment provider and turn its replies into one common shape.

Every provider names things differently ("success", "abandoned", amounts in
minor units...). normalize_result() maps a reply to the shape the rest of the
app uses, so adding a provider only means adding a client.
"""

from decimal import Decimal

from .allocation import to_money

STATUS_MAP = {
	"success": "Success",
	"successful": "Success",
	"paid": "Success",
	"failed": "Failed",
	"abandoned": "Failed",
	"reversed": "Failed",
}


def normalize_status(provider_status: str | None) -> str:
	"""
	Map a provider status to Success, Failed or Pending.

	Unknown statuses stay Pending, so the reconciliation job asks again later
	instead of guessing.

	Parameters:
		provider_status (str, optional): The status sent by the provider.

	Returns:
		str: "Success", "Failed" or "Pending".
	"""
	return STATUS_MAP.get((provider_status or "").strip().lower(), "Pending")


def from_minor_units(amount: int | str) -> Decimal:
	"""
	Convert an amount in minor units (cents, kobo, paise) to a Decimal.

	Parameters:
		amount (int | str, required): Amount in minor units, e.g. 150050.

	Returns:
		Decimal: Amount in major units, e.g. Decimal("1500.50").
	"""
	return to_money(Decimal(str(amount)) / 100)


def normalize_result(data: dict) -> dict:
	"""
	Turn a provider transaction object into the app's common shape.

	Parameters:
		data (dict, required): The provider's transaction object.

	Returns:
		dict: {"reference", "status", "amount", "currency"}.
	"""
	return {
		"reference": data.get("reference"),
		"status": normalize_status(data.get("status")),
		"amount": from_minor_units(data.get("amount") or 0),
		"currency": (data.get("currency") or "").upper(),
	}


class GatewayClient:
	"""Minimal HTTP client for a REST payment provider."""

	def __init__(self, base_url: str, secret_key: str, timeout: int = 20):
		"""
		Build a client.

		Parameters:
			base_url (str, required): Provider API root, e.g. "https://api.example-pay.com".
			secret_key (str, required): Provider secret key, sent as a Bearer token.
			timeout (int, optional): Request timeout in seconds.
		"""
		self.base_url = base_url.rstrip("/")
		self.secret_key = secret_key
		self.timeout = timeout

	def verify(self, reference: str) -> dict:
		"""
		Ask the provider for the current state of a transaction.

		Parameters:
			reference (str, required): Our transaction reference.

		Returns:
			dict: The normalized result (see normalize_result).
		"""
		import requests

		response = requests.get(
			f"{self.base_url}/transaction/verify/{reference}",
			headers={"Authorization": f"Bearer {self.secret_key}"},
			timeout=self.timeout,
		)
		response.raise_for_status()
		return normalize_result(response.json().get("data") or {})
