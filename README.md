# Frappe Payment Gateway Demo

A **provider-agnostic online payment flow for ERPNext** (Frappe v15 / v16). Customers pay one or more Sales Invoices online. The app confirms each payment through **three independent paths** and posts **exactly one Payment Entry**, never zero and never two.

> A showcase project written from scratch by [Aarti Manjare](https://github.com/aartimanjare) to demonstrate the integration patterns I use in production ERPNext work. It is not taken from any client codebase.

## Why this is harder than it looks

Payment providers notify you with webhooks, but webhooks get lost, arrive twice, or arrive at the same moment the customer's browser asks "did it work?". A naive integration either misses payments or books them twice. This app handles that:

| Problem | How the app handles it |
|---|---|
| Forged or tampered webhooks | HMAC-SHA512 signature over the **raw body**, compared in constant time; missing secret or signature means reject |
| Webhook never arrives | A scheduled **reconciliation job** asks the provider about anything still Pending after N minutes |
| Webhook and verify call race each other | The transaction row is locked (`SELECT … FOR UPDATE`) and only a **Pending** transaction is changed (idempotent) |
| Provider charged a different amount | Amount and currency are checked against the transaction; a mismatch marks it Failed with a clear error, and nothing is posted |
| One payment for several invoices | Allocated **oldest due date first**, using `Decimal` so rounding never creates or loses money |
| Paying someone else's invoice | `initiate` checks read permission, docstatus, outstanding amount, company, and that all invoices share one customer and currency |

## Flow

```
Customer ──initiate──▶ Payment Gateway Transaction (Pending, invoices + allocations)
                             │
     ┌───────────────────────┼─────────────────────────────┐
  webhook (signed)      verify (customer)        reconcile_pending (every 15 min)
     └───────────────────────┼─────────────────────────────┘
                             ▼
              apply_gateway_result()  ← row lock, Pending-only
                 ├─ Success → Payment Entry (submitted, allocated) → status Success
                 └─ Failed / mismatch → status Failed (+ error)
```

## What's inside

```
payment_gateway_demo/
├── gateway/                 # pure Python, unit-tested without Frappe
│   ├── signature.py         # HMAC-SHA512 webhook verification
│   ├── allocation.py        # split a payment across invoices (Decimal)
│   └── client.py            # provider HTTP client + reply normalization
├── services/
│   ├── posting.py           # idempotent apply + Payment Entry creation
│   └── reconciliation.py    # scheduled safety net
├── api/v1/payments.py       # initiate / webhook / verify (standard response envelope)
└── doctype/
    ├── demo_gateway_settings/            # credentials (Password fields), receiving account
    ├── payment_gateway_transaction/      # one payment attempt
    └── payment_gateway_transaction_reference/  # invoices + allocated amounts
```

**Design choices**
- **Pure core, thin Frappe layer:** the business rules (signature, allocation, normalization) have no Frappe import, so they're fast to test and easy to reuse.
- **Secrets in Password fields:** they're never logged or returned by the API.
- **Errors are isolated:** one failing transaction in the background job is logged and skipped, and never blocks the rest.
- **One response shape:** every endpoint returns `{"status", "message", "data"}`.

## API

| Endpoint | Who calls it | Purpose |
|---|---|---|
| `POST …api.v1.payments.initiate` | Logged-in customer | `{"invoices": ["SINV-0001", "SINV-0002"], "amount": 500}` → creates a Pending transaction and returns its reference |
| `POST …api.v1.payments.webhook` | Provider (guest) | Signed notification (`X-Signature` header) → applies the result |
| `POST …api.v1.payments.verify` | The customer who started the payment | `{"reference": "…"}` → asks the provider and applies the result |

Full path prefix: `/api/method/frappe_payment_gateway_demo.payment_gateway_demo`.

## Install

```bash
bench get-app https://github.com/aartimanjare/frappe_payment_gateway_demo
bench --site your-site install-app frappe_payment_gateway_demo
```
Then open **Demo Gateway Settings** and set the API base URL, secret key, webhook secret, company and receiving (Bank / Cash) account.

## Tests

The core logic is covered by fast unit tests that don't need a Frappe site:

```bash
python -m unittest discover -s tests -t . -v
```

CI (GitHub Actions) runs `ruff` and these tests on every push.

## Built with

Python · Frappe Framework · ERPNext · MariaDB · GitHub Actions. Developed with AI-assisted tooling (Claude Code) under code-review and testing standards.

## License

MIT
