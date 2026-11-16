"""Apply a provider result to a transaction, exactly once.

The same payment can be confirmed three ways (webhook, the customer's verify
call, the reconciliation job), sometimes at the same moment. The transaction
row is locked with SELECT ... FOR UPDATE and only a Pending transaction is
changed, so a payment is never posted twice and never lost.
"""

import json

import frappe
from frappe import _
from frappe.utils import flt, nowdate

from ..doctype.demo_gateway_settings.demo_gateway_settings import get_settings

TRANSACTION = "Payment Gateway Transaction"


def apply_gateway_result(transaction_name: str, result: dict) -> "frappe.model.document.Document":
	"""
	Record the provider's answer on a transaction and post the payment if it succeeded.

	Parameters:
		transaction_name (str, required): Payment Gateway Transaction name.
		result (dict, required): Normalized provider result ({"status", "amount", "currency", ...}).

	Returns:
		Document: The transaction, as it stands after this call.
	"""
	# Row lock: a second caller waits here until the first one commits.
	frappe.db.get_value(TRANSACTION, transaction_name, "name", for_update=True)
	transaction = frappe.get_doc(TRANSACTION, transaction_name)

	if transaction.status != "Pending":
		return transaction  # already handled by another confirmation path

	transaction.last_payload = json.dumps(result, default=str, indent=1)

	if result["status"] == "Failed":
		transaction.status = "Failed"
	elif result["status"] == "Success":
		mismatch = _amount_mismatch(transaction, result)
		if mismatch:
			transaction.status = "Failed"
			transaction.error = mismatch
		else:
			transaction.payment_entry = _create_payment_entry(transaction)
			transaction.status = "Success"

	transaction.save(ignore_permissions=True)
	return transaction


def _amount_mismatch(transaction, result: dict) -> str | None:
	"""Return an error message when the provider charged a different amount or currency."""
	if flt(result["amount"], 2) != flt(transaction.amount, 2) or result["currency"] != transaction.currency:
		return _("Provider reported {0} {1}, expected {2} {3}").format(
			result["currency"], result["amount"], transaction.currency, transaction.amount
		)
	return None


def _create_payment_entry(transaction) -> str:
	"""Create and submit one Payment Entry allocated across the transaction's invoices."""
	from erpnext.accounts.party import get_party_account

	settings = get_settings()
	payment_entry = frappe.new_doc("Payment Entry")
	payment_entry.update(
		{
			"payment_type": "Receive",
			"company": transaction.company,
			"posting_date": nowdate(),
			"party_type": "Customer",
			"party": transaction.customer,
			"paid_from": get_party_account("Customer", transaction.customer, transaction.company),
			"paid_to": settings.receiving_account,
			"paid_amount": transaction.amount,
			"received_amount": transaction.amount,
			"reference_no": transaction.gateway_reference,
			"reference_date": nowdate(),
			"remarks": _("Online payment {0}").format(transaction.gateway_reference),
		}
	)
	for row in transaction.references:
		payment_entry.append(
			"references",
			{
				"reference_doctype": "Sales Invoice",
				"reference_name": row.sales_invoice,
				"allocated_amount": row.allocated_amount,
			},
		)
	payment_entry.flags.ignore_permissions = True
	payment_entry.insert()
	payment_entry.submit()
	return payment_entry.name
