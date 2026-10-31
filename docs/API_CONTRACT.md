# API contract (each owner publishes their feature's endpoints, the other consumes them)

Base path `/api`. Session cookie auth (same origin through the Vite proxy). `A` = admin only, `S` = admin or staff, `C` = the signed-in customer's own data. Live docs: `http://localhost:8000/docs`.

## Conventions
- **Money:** strings with two decimals, for example `"560.00"`. Never floats. The frontend formats for display and never re-implements pricing math. Use `POST /api/pricing/preview` for live totals.
- **Dates:** ISO strings, `2026-10-31`. Timestamps are ISO with timezone.
- **Errors:** FastAPI's default shape, which `frontend/src/lib/api.ts` already reads. A single failure is `{"detail": "message"}`. Field validation failures are HTTP 422 with `{"detail": [{"loc": ["body", "password"], "msg": "message", "type": "..."}]}`, and the endpoint owner uses this for the password policy and other field rules so the form can show the message next to the field. 401 when signed out, 403 when the role is not allowed, 404 for another customer's record. Person B extends `ApiError` to carry the field list (step B1).
- **Lists:** `{"total": 0, "page": 1, "page_size": 20, "items": []}` with `?page=` and `?page_size=`, plus filters named in the table.
- **Enums** are the uppercase strings from `backend/app/enums.py`.
- A change to this file needs both people to agree in chat first.

## Endpoints
| Area | Endpoint | Who | Status |
|---|---|---|---|
| Auth | `POST auth/login`, `POST auth/logout`, `GET auth/me` | public / any | done |
| Auth | `POST auth/signup`, `POST auth/forgot-password`, `POST auth/reset-password` | public | done |
| Staff | `GET/POST users` | A | done |
| Customers | `GET/POST customers`, `GET/PUT/DELETE customers/{id}` | S | done |
| Products | `GET/POST products`, `GET/PUT/DELETE products/{id}`, variants nested in the product body | A (read: S) | done |
| Plans | `GET/POST plans`, `GET/PUT/DELETE plans/{id}` | A (read: S) | done |
| Taxes | `GET/POST taxes`, `PATCH taxes/{id}` | A (read: S) | done |
| Discounts | `GET/POST discounts`, `PATCH discounts/{id}` | A | done |
| Templates | `GET/POST quotation-templates`, `GET/PUT/DELETE quotation-templates/{id}` | S | done |
| Pricing | `POST pricing/preview` | any signed in | done |
| Subscriptions | `GET/POST subscriptions` (filters: status, customer, plan), `GET/PUT subscriptions/{id}` | S | done |
| Subscriptions | `POST subscriptions/{id}/transition` body `{"to": "CONFIRMED"}` | S | done |
| Subscriptions | `POST subscriptions/run-lifecycle` | A | done |
| Billing | `POST invoices/run-billing` body `{"as_of": "2026-10-31"}` (optional) | A | done |
| Invoices | `GET invoices` (filters: status, overdue, customer, from, to), `GET invoices/{id}` | S | done |
| Invoices | `POST invoices/{id}/confirm`, `/cancel`, `/send`, `GET invoices/{id}/print` | S | done |
| Payments | `GET/POST payments` (invoice_id, method, amount, payment_date, note) | S | done |
| Reports | `GET reports/summary`, `GET reports/overdue`, `GET reports/revenue-by-month` | S | done |
| Portal | `GET portal-subscriptions`, `GET portal-subscriptions/{id}`, transition and renew actions | C | done |
| Portal | `GET portal-invoices`, `GET portal-invoices/{id}`, `GET portal-invoices/{id}/print` | C | done |

## Billing run response (`POST invoices/run-billing`)
```json
{
  "created": 500,
  "skipped": 0,
  "errors": []
}
```
Each error identifies its subscription and period; failures do not stop other subscriptions from billing.

## Seed data
`uv run python -m app.seed` creates demo users, customers, products, plans, taxes and a discount. Person A adds a larger option (`--big`, step A9) that creates 5,000 subscriptions and their invoices and payments, so the frontend can test pagination and the 2-second target.
