"""Scheduled safety net: ask the provider about payments still Pending."""

import frappe
from frappe.utils import add_to_date, now_datetime

from ..doctype.demo_gateway_settings.demo_gateway_settings import get_settings
from ..gateway.client import GatewayClient
from .posting import TRANSACTION, apply_gateway_result


def reconcile_pending() -> None:
	"""
	Re-check Pending transactions older than the configured age.

	Runs every 15 minutes (hooks.py). One failing transaction is logged and
	skipped so it never blocks the others.

	Returns:
		None
	"""
	settings = frappe.get_cached_doc("Demo Gateway Settings")
	if not settings.enabled:
		return

	cutoff = add_to_date(now_datetime(), minutes=-(settings.reconcile_after_minutes or 15))
	pending = frappe.get_all(
		TRANSACTION,
		filters={"status": "Pending", "creation": ("<", cutoff)},
		fields=["name", "gateway_reference"],
		order_by="creation asc",
		limit=200,
	)
	if not pending:
		return

	settings = get_settings()
	client = GatewayClient(settings.base_url, settings.get_password("secret_key"))
	for row in pending:
		try:
			apply_gateway_result(row.name, client.verify(row.gateway_reference))
			frappe.db.commit()  # each transaction stands alone in a background job
		except Exception:
			frappe.db.rollback()
			frappe.log_error(title=f"Payment reconciliation failed: {row.name}")
