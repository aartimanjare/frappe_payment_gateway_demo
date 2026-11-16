from frappe.model.document import Document


class PaymentGatewayTransaction(Document):
	"""
	One online payment attempt.

	Created as Pending when the customer starts checkout; moved to Success or
	Failed exactly once, by whichever confirmation arrives first (webhook,
	verify call or the reconciliation job). See services/posting.py.
	"""
