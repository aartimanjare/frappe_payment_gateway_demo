"""Payment endpoints: start a payment, receive the provider webhook, verify on demand."""

import json

import frappe
from frappe import _
from frappe.utils import flt

from ...doctype.demo_gateway_settings.demo_gateway_settings import get_settings
from ...gateway.allocation import OpenInvoice, allocate
from ...gateway.client import GatewayClient, normalize_result
from ...gateway.signature import is_valid_signature
from ...services.posting import TRANSACTION, apply_gateway_result
from ..response import ok


@frappe.whitelist(methods=["POST"])
def initiate(invoices: str | list, amount: float | None = None) -> dict:
	"""
	Start an online payment for one or more Sales Invoices.

	Endpoint: /api/method/frappe_payment_gateway_demo.payment_gateway_demo.api.v1.payments.initiate
	Method: POST

	Parameters:
		invoices (list[str] | JSON string, required): Sales Invoice names, all for the same customer.
		amount (float, optional): Amount to pay; defaults to the full outstanding. Allocated oldest-due first.

	Returns:
		dict: {"status": true, "message": "", "data": {"reference", "amount", "currency", "transaction"}}
	"""
	names = json.loads(invoices) if isinstance(invoices, str) else invoices
	if not isinstance(names, list) or not names or not all(isinstance(name, str) for name in names):
		frappe.throw(_("Send a list of Sales Invoice names"))

	settings = get_settings()
	rows = _payable_invoices(names, settings.company)
	open_invoices = [OpenInvoice(row.name, str(row.due_date), row.outstanding_amount) for row in rows]
	pay_amount = amount if amount is not None else sum(flt(row.outstanding_amount) for row in rows)

	try:
		allocations = allocate(pay_amount, open_invoices)
	except ValueError as error:
		frappe.throw(str(error))

	transaction = frappe.get_doc(
		{
			"doctype": TRANSACTION,
			"gateway_reference": frappe.generate_hash(length=20),
			"customer": rows[0].customer,
			"company": settings.company,
			"currency": rows[0].currency,
			"amount": float(sum(share for _name, share in allocations)),
			"references": [
				{"sales_invoice": name, "allocated_amount": float(share)} for name, share in allocations
			],
		}
	).insert(ignore_permissions=True)

	# A real integration would now call the provider's "initialize" API and
	# return its checkout URL; the reference is what ties both sides together.
	return ok(
		{
			"transaction": transaction.name,
			"reference": transaction.gateway_reference,
			"amount": transaction.amount,
			"currency": transaction.currency,
		}
	)


@frappe.whitelist(allow_guest=True, methods=["POST"])
def webhook() -> dict:
	"""
	Receive the provider's payment notification.

	Endpoint: /api/method/frappe_payment_gateway_demo.payment_gateway_demo.api.v1.payments.webhook
	Method: POST (called by the provider, not by users)

	The raw body must carry a valid HMAC-SHA512 signature in the X-Signature
	header; anything else is rejected before the body is even parsed.

	Returns:
		dict: {"status": true, "message": "", "data": {"transaction_status"}}
	"""
	settings = get_settings()
	payload = frappe.request.get_data()
	signature = frappe.get_request_header("X-Signature")
	if not is_valid_signature(payload, signature, settings.get_password("webhook_secret")):
		raise frappe.AuthenticationError(_("Invalid webhook signature"))

	result = normalize_result(json.loads(payload).get("data") or {})
	name = frappe.db.get_value(TRANSACTION, {"gateway_reference": result["reference"]}, "name")
	if not name:
		return ok({"transaction_status": None}, "Unknown reference, ignored")

	transaction = apply_gateway_result(name, result)
	return ok({"transaction_status": transaction.status})


@frappe.whitelist(methods=["POST"])
def verify(reference: str) -> dict:
	"""
	Ask the provider for the latest status of one of the caller's payments.

	Endpoint: /api/method/frappe_payment_gateway_demo.payment_gateway_demo.api.v1.payments.verify
	Method: POST

	Parameters:
		reference (str, required): The gateway reference returned by initiate.

	Returns:
		dict: {"status": true, "message": "", "data": {"transaction_status", "payment_entry"}}
	"""
	if not isinstance(reference, str) or not reference:
		frappe.throw(_("reference must be a non-empty string"))

	name = frappe.db.get_value(TRANSACTION, {"gateway_reference": reference}, "name")
	if not name:
		frappe.throw(_("Payment {0} not found").format(reference), frappe.DoesNotExistError)
	if frappe.db.get_value(TRANSACTION, name, "owner") != frappe.session.user:
		frappe.throw(_("Not permitted"), frappe.PermissionError)

	settings = get_settings()
	client = GatewayClient(settings.base_url, settings.get_password("secret_key"))
	transaction = apply_gateway_result(name, client.verify(reference))
	return ok({"transaction_status": transaction.status, "payment_entry": transaction.payment_entry})


def _payable_invoices(names: list[str], company: str) -> list:
	"""Load the invoices, checking each is submitted, open, readable and for one customer/currency."""
	rows = frappe.get_all(
		"Sales Invoice",
		filters={"name": ("in", names)},
		fields=["name", "customer", "company", "currency", "docstatus", "outstanding_amount", "due_date"],
	)
	if len(rows) != len(set(names)):
		frappe.throw(_("One or more invoices were not found"))

	for row in rows:
		if not frappe.has_permission("Sales Invoice", "read", row.name):
			frappe.throw(_("Not permitted to pay {0}").format(row.name), frappe.PermissionError)
		if row.docstatus != 1 or flt(row.outstanding_amount) <= 0:
			frappe.throw(_("Invoice {0} is not open for payment").format(row.name))
		if row.company != company:
			frappe.throw(_("Invoice {0} belongs to another company").format(row.name))

	if len({row.customer for row in rows}) > 1 or len({row.currency for row in rows}) > 1:
		frappe.throw(_("All invoices must be for the same customer and currency"))
	return rows
