"""Webhook signature checks.

Pure functions with no Frappe import, so they can be unit tested on their own.
The provider signs the raw request body with HMAC-SHA512 using the shared
webhook secret and sends the hex digest in a header.
"""

import hashlib
import hmac


def compute_signature(payload: bytes, secret: str) -> str:
	"""
	Return the HMAC-SHA512 hex digest of the raw payload.

	Parameters:
		payload (bytes, required): The raw request body, exactly as received.
		secret (str, required): The shared webhook secret.

	Returns:
		str: Lower-case hex digest.
	"""
	return hmac.new(secret.encode(), payload, hashlib.sha512).hexdigest()


def is_valid_signature(payload: bytes, signature: str | None, secret: str | None) -> bool:
	"""
	Check a webhook signature in constant time.

	Any missing piece counts as invalid, so a misconfigured site rejects
	webhooks instead of accepting unsigned ones.

	Parameters:
		payload (bytes, required): The raw request body.
		signature (str, optional): The hex digest sent by the provider.
		secret (str, optional): The shared webhook secret.

	Returns:
		bool: True only when the signature matches.
	"""
	if not payload or not signature or not secret:
		return False
	return hmac.compare_digest(compute_signature(payload, secret), signature.strip().lower())
