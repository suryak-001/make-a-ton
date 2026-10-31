# API contract (Person A publishes, Person B consumes)

Base path `/api`. Session cookie auth (same origin through the Vite proxy). `A` = admin only, `S` = admin or staff, `C` = the signed-in customer's own data. Live docs: `http://localhost:8000/docs`.

## Conventions
- **Money:** strings with two decimals, for example `"560.00"`. Never floats. The frontend formats for display and never re-implements pricing math. Use `POST /api/pricing/preview` for live totals.
- **Dates:** ISO strings, `2026-10-31`. Timestamps are ISO with timezone.
- **Errors:** FastAPI's default shape, which `frontend/src/lib/api.ts` already reads. A single failure is `{"detail": "message"}`. Field validation failures are HTTP 422 with `{"detail": [{"loc": ["body", "password"], "msg": "message", "type": "..."}]}`, and Person A uses this for the password policy and other field rules so the form can show the message next to the field. 401 when signed out, 403 when the role is not allowed, 404 for another customer's record. Person B extends `ApiError` to carry the field list.
- **Lists:** `{"count": 0, "page": 1, "page_size": 25, "results": []}` with `?page=` and `?page_size=`, plus filters named in the table.
- **Enums** are the uppercase strings from `backend/app/enums.py`.
- A change to this file needs both people to agree in chat first.

## Endpoints
| Area | Endpoint | Who | Status |
|---|---|---|---|
| Auth | `POST auth/login`, `POST auth/logout`, `GET auth/me` | public / any | done |
| Auth | `POST auth/signup`, `POST auth/password-reset`, `POST auth/password-reset/confirm` | public | todo |
| Staff | `GET/POST users`, `PATCH users/{id}` | A | todo |
| Customers | `GET/POST customers`, `GET/PATCH customers/{id}` | S | todo |
| Products | `GET/POST products`, `GET/PATCH products/{id}`, variants nested in the product body | A (read: S) | todo |
| Plans | `GET/POST plans`, `GET/PATCH plans/{id}` | A (read: S) | todo |
| Taxes | `GET/POST taxes`, `PATCH taxes/{id}` | A (read: S) | todo |
| Discounts | `GET/POST discounts`, `GET/PATCH discounts/{id}` | A (read: S) | todo |
| Templates | `GET/POST quotation-templates`, `GET/PATCH quotation-templates/{id}` | A (read: S) | todo |
| Pricing | `POST pricing/preview` | any signed in | done |
| Subscriptions | `GET/POST subscriptions` (filters: status, customer, plan), `GET/PATCH subscriptions/{id}` | S | todo |
| Subscriptions | `POST subscriptions/{id}/transition` body `{"to": "CONFIRMED"}` | S | todo |
| Subscriptions | `POST subscriptions/run-lifecycle` | S | todo |
| Billing | `POST invoices/run-billing` body `{"as_of": "2026-10-31"}` (optional) | S | todo |
| Invoices | `GET invoices` (filters: status, overdue, customer, from, to), `GET invoices/{id}` | S | todo |
| Invoices | `POST invoices/{id}/confirm`, `/cancel`, `/send`, `GET invoices/{id}/print` | S | todo |
| Payments | `GET/POST payments` (invoice_id, method, amount, payment_date, note) | S | todo |
| Reports | `GET reports/summary` (filters: from, to, plan, customer, status), `GET reports/overdue`, `GET reports/revenue-by-month` | S | todo |
| Portal | `GET portal/subscriptions`, `GET portal/subscriptions/{id}`, `POST portal/subscriptions/{id}/pause\|close\|renew` | C | todo |
| Portal | `GET portal/invoices`, `GET portal/invoices/{id}`, `GET portal/invoices/{id}/print` | C | todo |

## Billing run response (`POST invoices/run-billing`)
```json
{
  "as_of": "2026-10-31",
  "due": 500,
  "created": 500,
  "already_billed": 0,
  "skipped": 0,
  "failed": 0,
  "errors": []
}
```
`due = created + already_billed + skipped + failed` must always hold. The Billing Run page shows that equation.

## Seed data
`uv run python -m app.seed` creates demo users, customers, products, plans, taxes and a discount. Person A adds a larger option (`--big`) that creates 5,000 subscriptions and their invoices and payments, so the frontend can test pagination and the 2-second target.
