# API contract (each owner publishes their feature's endpoints, the other consumes them)

Base path `/api`. Session cookie auth (same origin through the Vite proxy). `A` = admin only, `S` = admin or staff, `C` = the signed-in customer's own data. Live docs: `http://localhost:8000/docs`.

## Conventions
- **Money:** strings with two decimals, for example `"560.00"`. Never floats. The frontend formats for display and never re-implements pricing math. Use `POST /api/pricing/preview` for live totals.
- **Dates:** ISO strings, `2026-10-31`. Timestamps are ISO with timezone.
- **Errors:** a single failure is `{"detail": "message"}`. A failure tied to a form field is `{"detail": [{"loc": ["body", "password"], "msg": "message"}]}` (FastAPI's own 422 format), so `ApiError` in `frontend/src/lib/api.ts` shows either one. 401 when signed out, 403 when the role is not allowed, 404 for another customer's record, 409 for conflicts.
- **Lists:** `{"items": [], "total": 0, "page": 1, "page_size": 20}` with `?page=` and `?page_size=` (default 20, maximum 100), plus the filters named in the table.
- **Enums** are the uppercase strings from `backend/app/enums.py`.
- A change to this file needs both people to agree in chat first.

## Endpoints
Updates use `PUT`, except taxes and discounts which use `PATCH`. Status: **done** means built, merged to `main` and covered by backend tests.

| Area | Endpoint | Who | Status |
|---|---|---|---|
| Auth | `POST auth/signup`, `POST auth/login`, `POST auth/logout`, `GET auth/me` | public / any | done |
| Auth | `POST auth/forgot-password`, `POST auth/reset-password` | public | done |
| Staff | `GET/POST users` | A | done |
| Customers | `GET/POST customers`, `GET/PUT/DELETE customers/{id}` | S | done |
| Products | `GET/POST products`, `GET/PUT/DELETE products/{id}` (variants in the body) | A (read: S) | done |
| Plans | `GET/POST plans`, `GET/PUT/DELETE plans/{id}` | A (read: S) | done |
| Templates | `GET/POST quotation-templates`, `GET/PUT/DELETE quotation-templates/{id}`, `POST quotation-templates/{id}/create-subscription` | A (read: S) | done |
| Subscriptions | `GET/POST subscriptions` (filters: status, customer, plan), `GET/PUT/DELETE subscriptions/{id}` | S | done |
| Subscriptions | `POST subscriptions/{id}/transition` body `{"to": "CONFIRMED", "reason": null}`, `POST subscriptions/{id}/renew`, `POST subscriptions/run-lifecycle` | S | done |
| Portal | `GET portal/subscriptions`, `GET portal/subscriptions/{id}`, `POST portal/subscriptions/{id}/transition`, `POST portal/subscriptions/{id}/renew` | C | done |
| Pricing | `POST pricing/preview` | any signed in | done |
| Taxes | `GET/POST taxes`, `PATCH taxes/{id}` | A (read: S) | done |
| Discounts | `GET/POST discounts`, `PATCH discounts/{id}` | A (read: S) | done |
| Billing | `POST invoices/run-billing` body `{"as_of": "2026-10-31"}` (optional) | S | done |
| Invoices | `GET invoices` (filters: status, overdue, customer, from, to), `GET invoices/{id}` | S | done |
| Invoices | `POST invoices/{id}/confirm`, `/cancel`, `/send`, `GET invoices/{id}/print` | S | done |
| Payments | `GET/POST payments` (invoice_id, method, amount, payment_date, note) | S | done |
| Reports | `GET reports/summary`, `GET reports/overdue`, `GET reports/revenue-by-month` (summary takes dates only for now, see PLAN.md open work) | S | done |
| Portal | `GET portal/invoices`, `GET portal/invoices/{id}`, `GET portal/invoices/{id}/print` | C | done |

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
`uv run python -m app.seed` creates demo users, customers, products, plans, taxes and a discount. Add `--big` (`uv run python -m app.seed --big`) for 5,000 subscriptions, so pagination and the 2-second target can be tested. A recorded benchmark is still open work (step M9).
