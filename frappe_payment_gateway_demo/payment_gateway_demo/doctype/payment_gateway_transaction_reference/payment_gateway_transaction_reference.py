from frappe.model.document import Document


class PaymentGatewayTransactionReference(Document):
	"""One invoice settled by a gateway transaction, with the amount allocated to it."""
