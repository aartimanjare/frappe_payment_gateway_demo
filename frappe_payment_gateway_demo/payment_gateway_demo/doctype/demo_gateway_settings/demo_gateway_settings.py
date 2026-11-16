import frappe
from frappe import _
from frappe.model.document import Document


class DemoGatewaySettings(Document):
	"""Provider credentials and the accounts payments are posted to."""

	def validate(self):
		"""Refuse a receiving account from another company or of the wrong type."""
		if not (self.company and self.receiving_account):
			return
		account = frappe.db.get_value(
			"Account", self.receiving_account, ["company", "account_type", "is_group"], as_dict=True
		)
		if account.company != self.company:
			frappe.throw(
				_("Receiving Account {0} belongs to {1}, not {2}").format(
					self.receiving_account, account.company, self.company
				)
			)
		if account.is_group or account.account_type not in ("Bank", "Cash"):
			frappe.throw(_("Receiving Account must be a Bank or Cash ledger account"))


def get_settings() -> "DemoGatewaySettings":
	"""
	Return the enabled settings or stop with a clear message.

	Returns:
		DemoGatewaySettings: The single settings document.
	"""
	settings = frappe.get_cached_doc("Demo Gateway Settings")
	if not settings.enabled:
		frappe.throw(_("Online payments are not enabled in Demo Gateway Settings"))
	return settings
