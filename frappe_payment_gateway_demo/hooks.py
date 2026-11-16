app_name = "frappe_payment_gateway_demo"
app_title = "Payment Gateway Demo"
app_publisher = "Aarti Manjare"
app_description = "Provider-agnostic online payment flow for ERPNext"
app_email = "aartimanjare@gmail.com"
app_license = "mit"

required_apps = ["erpnext"]

# Webhooks can be lost (network errors, provider retries giving up), so a
# periodic job asks the provider about anything still pending.
scheduler_events = {
	"cron": {
		"*/15 * * * *": [
			"frappe_payment_gateway_demo.payment_gateway_demo.services.reconciliation.reconcile_pending",
		],
	},
}
