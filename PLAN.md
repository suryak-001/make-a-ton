# Subscription Management System: Build Plan for 2 People

Source: `Subscription_Management_System.pdf` (Brightloop Software scenario).
Requirements and decisions: **[docs/PRD.md](docs/PRD.md)**. API contract between the two halves: **[docs/API_CONTRACT.md](docs/API_CONTRACT.md)**.

**Person A = backend** (`backend/`). **Person B = frontend** (`frontend/`).

---

## 1. What we're building

One web app that runs a subscription business from start to finish: **catalog → quotation → subscription → invoice → payment → reporting**, for one company, Brightloop.

| # | Scene | Delivers |
|---|-------|----------|
| R1 | Sign up and auth | Unique email, password of at least 9 characters with upper, lower and special, reset link by email |
| R2 | Roles | Admin, staff and customer portal. Only admin creates staff |
| R3 | Products | Name, type, sales and cost price, notes, variants with extra price (Odoo +560) |
| R4 | Plans | Price, daily, weekly, monthly or yearly, minimum quantity, availability dates, per-plan auto-close, closable, pausable, renewable |
| R5 | Quotation templates | Preset plan and lines, validity in days |
| R6 | Subscriptions | Number, customer, plan, dates, payment terms, lines. Draft → Quotation → Confirmed → Active → Closed (plus Paused) |
| R7 | Billing day | Bulk invoices from subscriptions, confirm, cancel, send, print. Draft → Confirmed → Paid. No double-billing, no skipped periods |
| R8 | Taxes | Admin rules, applied automatically |
| R9 | Discounts | Admin only, fixed or percent, minimums, dates, usage limit, appears on the next invoice by itself |
| R10 | Payments | Method, amount, date, note, against an invoice. Paid, outstanding, overdue |
| R11 | Reports | One dashboard with filters and a summary, every page under 2 seconds |

Decisions where the brief is vague are in **docs/PRD.md** (Paused state, partial payments, discount counting, Invoiced versus Collected revenue, and others).

---

## 2. Stack

| Layer | Choice |
|-------|--------|
| API | FastAPI, Python 3.13 (managed by `uv`), OpenAPI docs at `/docs` |
| DB | PostgreSQL, SQLAlchemy 2, Alembic |
| Money | `Decimal(12,2)` in the DB, strings in JSON |
| Auth | bcrypt and a signed `HttpOnly` session cookie |
| Email | `smtplib`, printed to the server console in development |
| Frontend | React 19, TypeScript, Vite, Tailwind 4, React Router, TanStack Query |
| Tests | pytest on the backend, `tsc` and oxlint on the frontend |

The browser only talks to the Vite dev server, which proxies `/api` to FastAPI, so the cookie is same-origin and no CORS setup is needed.

---

## 3. How we split the work: by layer

| | Person A: Backend | Person B: Frontend |
|---|---|---|
| Owns | `backend/` | `frontend/` |
| Branch | `main` or short `backend/*` branches | `frontend` branch, merged to `main` often |
| Delivers | Models, migrations, API, billing engine, tests, seed | Every screen, forms, validation messages, dashboard, portal |

**Why this works:** the data model, pricing engine, auth and the nav shell already exist (Phase 0, see section 4). Person B builds screens against the real API as endpoints land, and against mock data before that.

**Rules**
1. Each person edits only their own folder. If you need a change in the other folder, ask in chat.
2. `backend/app/models` and Alembic migrations are Person A's. B asks for fields. One migration per PR.
3. The API contract is frozen in **docs/API_CONTRACT.md**. A change needs both people to agree.
4. Short branches, small pull requests, merge to `main` at least every hour. Rebase on `main` before a PR. No force pushes.
5. Commit from your own account with messages that say why. Never commit secrets (`.env` stays ignored).
6. Both people write tests for their own half, and both can explain every file.
7. **Build feature by feature.** Both halves of a feature are finished and run together end to end before either person starts the next feature (section 7). Do not let one layer run ahead by more than one feature.
8. **Integrate every hour.** Merge to `main` hourly. The moment a backend endpoint lands, the frontend swaps its mock data for the real call.
9. **Cross-explain.** After each feature, each person spends about 5 minutes walking the other through their half, especially billing. Anyone may be asked about any file at the desk.

---

## 4. Phase 0 (done)

Scaffolded 2026-10-31: skeleton, full schema and first Alembic migration, login and logout with role guards on API and UI, nav shell with placeholder pages, contract stubs, a tested pricing engine (also at `POST /api/pricing/preview`), and the seed script. See `README.md`.

Still to do together: review the schema once, and agree the API contract in `docs/API_CONTRACT.md`.

---

## 5. Person A: Backend

| Step | Deliverable | Done when |
|------|-------------|-----------|
| **A1. Auth** | Signup (unique email, password policy in `core/security.py`), password reset by emailed single-use token (hashed, expires in 1 hour), `require_roles` on every router | Weak passwords and duplicate emails are rejected with field messages. A customer gets 403 on `/products` |
| **A2. Users and customers** | Admin-only staff creation. Customer CRUD (staff and admin) | Staff cannot call the users endpoints |
| **A3. Catalogue** | Products with variants, plans, taxes, discounts, quotation templates | The Odoo variant adds 560. Plans outside their dates cannot be picked for a new subscription |
| **A4. Seed** | Extend `app/seed.py`, then add `--big` (5,000 subscriptions, their invoices and payments). **Hand to B by hour 2** | B can log in and see realistic lists and a large dataset |
| **A5. Subscriptions** | Create from a template, auto number, lines through the pricing engine, state machine in `services/subscriptions.py`, Paused, renew, close, lifecycle job (auto-close at expiry) | Illegal transitions are rejected. Becoming Active sets `next_invoice_date` |
| **A6. Billing engine** | `generate_invoice_for_period` and `run_billing` in `services/billing.py`: unique `(subscription_id, period_start)`, invoice and `next_invoice_date` in one transaction, `with_for_update(skip_locked=True)`, catch-up, failures recorded and the run continues, invoice numbers from the `Sequence` table | Run three times: invoice count unchanged. A subscription three periods behind gets exactly 3 invoices. Two runs at once create no duplicates |
| **A7. Discounts in billing** | Applicable discounts found at invoice time, `DiscountUsage` plus `used_count` updated with the discount row locked | 20 concurrent uses of a limit-5 discount apply exactly 5 times. It stops on expiry |
| **A8. Invoices and payments** | Confirm, cancel, send (email), print page. Record payments, partial allowed, overpayment blocked, auto-mark Paid | Every transition is guarded. Outstanding updates immediately |
| **A9. Reports** | SQL aggregates for the summary, overdue list and revenue by month, with filters | All numbers come from `func.sum` and `group_by`, never from loading rows into Python |
| **A10. Portal API** | `/portal/*` endpoints scoped to the signed-in customer | Another customer's record returns 404 |
| **A11. Performance and tests** | Indexes checked with `EXPLAIN`, pagination everywhere, tests for transitions, billing twice, discount limit and portal access | Every endpoint under 2 seconds on the `--big` seed. Measured and noted for the demo |

---

## 6. Person B: Frontend

Pages live in `frontend/src/pages/<route>/index.tsx` and are registered automatically by `routes.tsx`. Menu entries are in `src/nav.ts`. Shared primitives are in `src/components/ui.tsx`.

| Step | Deliverable | Done when |
|------|-------------|-----------|
| **B1. Foundation** | Extend the existing API client so `ApiError` carries FastAPI's 422 field messages, money and date formatters (money stays a string until display), reusable form, table, pagination and status-badge components, mock data until endpoints land | One shared way to call the API and show errors |
| **B2. Public pages** | Signup with live password hints, login, forgot password, reset password | Weak passwords show the rule that failed. Duplicate email shows the server message |
| **B3. Role shell** | Menu and routes by role, Forbidden page | Staff never see admin menu items. The server still enforces access |
| **B4. Admin screens** | Products with an inline variant editor, plans (with the four switches), taxes, discounts, quotation templates, staff creation | Forms validate before submit and show server errors per field |
| **B5. Staff screens** | Customers, subscriptions list (server-paginated, filtered) and detail with a state pipeline and action buttons that appear only when allowed, quote builder from a template using `POST /api/pricing/preview` | Totals on screen always match what the server stores |
| **B6. Billing Run page** | One button, live counts for due, created, already billed, skipped and failed, the equation shown, a "Run again" button, an "as of" date | Second run shows 0 created. The counts add up on screen |
| **B7. Invoices and payments** | Invoice list (filters: status, overdue, customer, dates) and detail, confirm, cancel, send, print-CSS page, payment form on the invoice, paid, outstanding and overdue badges | Illegal actions are hidden or disabled with a reason |
| **B8. Finance dashboard** | Cards for active subscriptions, MRR, invoiced, collected, outstanding, overdue, revenue-by-month chart, overdue table, filters, metric definitions in tooltips | Loads in under 2 seconds on the `--big` seed |
| **B9. Customer portal** | My subscriptions (pause, close or renew when the plan allows), my invoices and print view | A customer only ever sees their own records |
| **B10. Polish** | Empty and loading states, responsive layout, debounced search (about 300 ms), pagination on every list, lint and build clean | `npm run build` and `npm run lint` pass |

---

## 7. Timeline: feature by feature

Written for the 8-hour virtual round (hours from the start). Phase 0 is already done. If the 24-hour final applies, scale each block up by about 3.

Each feature below is built by both people in parallel against the frozen API contract, then **checked together end to end** before the next one starts. The step IDs refer to sections 5 and 6.

| Hours | Feature | Person A (backend) | Person B (frontend) | Done when (check it together) |
|-------|---------|--------------------|---------------------|-------------------------------|
| 0 to 0.5 | **Kick-off** | Review the schema, agree `docs/API_CONTRACT.md` | Same | Contract frozen, both can run the app |
| 0.5 to 1.5 | **F1. Accounts and roles** | A1, A2, start A4 (seed) | B1, B2, B3 | Sign up with a weak password and a duplicate email shows the right messages. Admin adds staff. Staff and customer menus differ. **Seed ready by 1.5** |
| 1.5 to 2.5 | **F2. Catalogue** | A3 (products, variants, plans, taxes, discounts, templates) | B4 (admin screens) | Create a product with the Odoo variant (+560), a plan and a tax in the UI, and see them in the list |
| 2.5 to 3.75 | **F3. Quotes and subscriptions** | A5 (subscriptions, state machine, Paused) | B5 (list, detail, state pipeline, quote builder) | Start from a template, walk Draft to Active in the UI, and an illegal move is refused |
| 3.75 to 5.25 | **F4. Billing and invoices** | A6, A7, A8 (invoices part) | B6 (Billing Run page), B7 (invoices) | Run billing: counts balance and invoices show tax and discount. Run again: 0 created. Move the date: only the missed periods are billed |
| 5.25 to 6.5 | **F5. Payments, dashboard, portal** | A8 (payments), A9, A10 | B7 (payment form), B8, B9 | Record partial and full payments, see Paid and overdue, the dashboard matches, a customer sees only their own data. **Feature freeze at 6.5** |
| 6.5 to 7.25 | **Harden** | A11 (tests, `--big` seed, `EXPLAIN`) | B10 (polish, empty states, lint and build) | Everything under 2 seconds on the big seed |
| 7.25 to 8 | **Submit** | README, clean-clone test, demo rehearsal, submit **before the deadline** | Same | The demo script in section 10 runs without a hitch |

**Rebalancing:** if A is behind at hour 4, B takes the reports or portal endpoints (A9, A10), which are mostly queries. If B is behind, trim polish, not features.

**If time runs short, cut in this order:** portal self-service actions, send-by-email polish, extra dashboard filters, the revenue chart. Never cut the Billing Run, the invoice screens, roles or validation.

---

## 8. Risks

| Risk | Mitigation |
|------|-----------|
| B blocked waiting for endpoints | B builds against mock data from the frozen contract, and auth, pricing and the seed already work |
| Double billing under concurrency | DB `UNIQUE(subscription_id, period_start)`, one transaction, row locks. On `IntegrityError` return the existing invoice |
| Invoice numbers clash or gap | The `Sequence` table is updated inside the invoice transaction, so a rollback leaves no gap |
| Slow dashboard with thousands of rows | SQL aggregates, indexes, server-side pagination |
| Frontend shows different totals from the server | B always calls `POST /api/pricing/preview` and never re-implements the math |
| Schema merge conflicts | A owns models and migrations. One migration per PR |
| Scope creep | Nice-to-haves only after the end-to-end demo works |

---

## 9. Nice-to-haves (only if ahead)
Customer self-service polish, PDF invoice attachment, reminder emails for overdue invoices, a subscription activity timeline, overdue aging buckets, proration, an optional "draft a quote from a sentence" AI helper (human confirms every result, the app works fully without it), CSV export.

---

## 10. Demo script (maps to the brief's scenes)

1. **Sign up** a new customer. Show the password rules, duplicate email rejection and the reset link.
2. **Admin** adds staff. Staff cannot open Discounts. The customer portal shows only that customer's data.
3. **Launch a plan:** a product with the Odoo variant (+560), then a monthly plan.
4. **Quote → subscription:** staff starts from a template and moves Draft → Quotation → Confirmed → Active.
5. **Discount:** admin creates "10% off for 10 or more seats, 5 uses".
6. **Billing day:** click *Run billing*. Invoices appear with the discount applied and the counts balance. Click again: **0 new invoices**. Move the date forward: exactly the missed periods are billed.
7. **Money comes in:** record a partial payment, then the rest. The invoice turns Paid. Show the overdue list.
8. **Finance lead:** open the dashboard on the 5,000-subscription seed, apply filters, and point at the load time.
