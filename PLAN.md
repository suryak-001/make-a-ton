# Subscription Management System: Build Plan for 2 People

Source: `Subscription_Management_System.pdf` (Brightloop Software scenario).
Requirements and decisions: **[docs/PRD.md](docs/PRD.md)**. API contract between the two halves: **[docs/API_CONTRACT.md](docs/API_CONTRACT.md)**.

**Person A = Money side** (taxes, discounts, billing, invoices, payments, reports). **Person B = Sell side** (auth, catalogue, subscriptions, portal). Each person builds their features end to end, backend and frontend.

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

## 3. How we split the work: by feature (each person owns whole features)

Each person owns complete features from the database through the API to the screen, and tests them. Nobody waits for the other half of their own feature.

| | **Person A: Money side** (backend-strong) | **Person B: Sell side** (frontend-strong) |
|---|---|---|
| Scenes | R7 billing day, R8 taxes, R9 discounts, R10 payments, R11 reports | R1 sign up, R2 roles, R3 products, R4 plans, R5 templates, R6 subscriptions |
| Hard part | Billing engine, discount limits under concurrency, report performance | Subscription state machine, quote builder, role-guarded screens |
| Volume | Fewer screens, harder logic | More screens, more routine CRUD |
| Also owns | Portal invoices page | Customers, portal subscriptions page |

Person A plays to a backend strength on the hard logic and builds the smaller set of screens. Person B plays to a frontend strength on a large set of screens and writes the routine backend CRUD for them, copying the patterns already in `backend/app/routers/auth.py` and `services/pricing.py`.

**Who owns which files** (to avoid merge conflicts, each feature lives in its own files)
```
backend/app/routers/<feature>.py, backend/app/services/<feature>.py     the feature's owner
frontend/src/pages/<route>/index.tsx                                      the feature's owner (auto-registered by routes.tsx)
backend/tests/test_<feature>.py                                           the feature's owner
A: taxes, discounts, invoices, payments, reports, pricing, portal_invoices, services/billing.py, services/discounts.py
B: users, customers, products, plans, quotation_templates, subscriptions, portal_subscriptions, services/subscriptions.py, core/* and routers/auth.py
```
**Shared, change only after telling the other person:** `backend/app/models/*` (one Alembic migration per PR), `backend/app/seed.py` (A edits the money sections, B edits the sell sections), `frontend/src/nav.ts`, `frontend/src/components/ui.tsx` (add new primitives, do not restyle existing ones), `frontend/src/lib/api.ts`.

**Rules**
1. The API contract in **docs/API_CONTRACT.md** is frozen at kick-off. Each owner publishes their own endpoints, and the other consumes them. A change needs both people to agree in chat.
2. Short branches, small pull requests, merge to `main` at least every hour. Rebase on `main` before a PR. No force pushes.
3. Commit from your own account with messages that say why. Never commit secrets (`.env` stays ignored).
4. A feature is done only when its API, its screen and its tests all work. Say "done" only after you have clicked through it.
5. **Cross-explain.** After each checkpoint, each person spends about 5 minutes walking the other through their code, especially billing and the state machine. Anyone may be asked about any file at the desk.
6. **Cross-test.** In the harden phase each person tries to break the other's features.

**The one dependency between you:** billing needs Active subscriptions. A builds and tests billing against seeded Active subscriptions, so A never waits. B's state machine must set `next_invoice_date` when a subscription becomes Active (the handoff contract in `docs/API_CONTRACT.md` and the stubs in `backend/app/services/`).

---

## 4. Phase 0 (done)

Scaffolded 2026-10-31: skeleton, full schema and first Alembic migration, login and logout with role guards on API and UI, nav shell with placeholder pages, contract stubs, a tested pricing engine (also at `POST /api/pricing/preview`), and the seed script. See `README.md`.

Still to do together at kick-off: review the schema once and agree the API contract.

---

## 5. Person A: Money side

Every step ships the API, the screen and tests.

| Step | Deliverable | Done when |
|------|-------------|-----------|
| **A1. Taxes** | Admin-only tax CRUD (API and screen). Taxes apply to subscription lines through the pricing engine | A tax created in the UI changes a quote total |
| **A2. Discounts** | Admin-only discount CRUD with all rules (fixed or percent, minimum purchase or quantity, dates, usage limit, product or subscription scope) and screen | An invalid rule is refused with a field message |
| **A3. Invoice generation** | `generate_invoice_for_period` in `services/billing.py`: snapshot lines, taxes, applicable discounts, `DiscountUsage` with the discount row locked, number from the `Sequence` table, all in one transaction | Same period twice returns the existing invoice. Twenty concurrent uses of a limit-5 discount apply exactly 5 times |
| **A4. Billing run and page** | `run_billing` (`<= as_of`, `with_for_update(skip_locked=True)`, catch-up, failures recorded and the run continues) and the **Billing Run page** with live counts that add up, a "Run again" button and an "as of" date | Run three times: count unchanged. Three periods behind gives exactly 3 invoices. The counts add up on screen |
| **A5. Invoices** | List (filters: status, overdue, customer, dates), detail, confirm, cancel, send (email), print page. Every transition is guarded | Illegal actions are refused by the server and hidden or disabled in the UI |
| **A6. Payments** | Record method, amount, date and note against an invoice. Partial allowed, overpayment blocked, auto-mark Paid. Payments list | Outstanding updates immediately and the overdue badge shows |
| **A7. Reports and dashboard** | SQL aggregates for the summary, overdue list and revenue by month, with filters. Dashboard with cards, chart, overdue table and metric definitions in tooltips | Every number comes from `func.sum` and `group_by`. Loads in under 2 seconds |
| **A8. Portal invoices** | `/portal/invoices` endpoints scoped to the signed-in customer, plus the page and print view | Another customer's invoice returns 404 |
| **A9. Performance** | `--big` seed (5,000 subscriptions with invoices and payments), indexes checked with `EXPLAIN`, pagination everywhere | Every page under 2 seconds. Measured and noted for the demo |

---

## 6. Person B: Sell side

Every step ships the API, the screen and tests. Pages live in `frontend/src/pages/<route>/index.tsx`.

| Step | Deliverable | Done when |
|------|-------------|-----------|
| **B1. Auth and roles** | Signup (unique email, password policy in `core/security.py`) with live hints, password reset by emailed single-use token (hashed, expires in 1 hour), forgot and reset pages, role shell and Forbidden page. Extend `ApiError` to carry FastAPI's 422 field messages | Weak passwords and duplicate emails show the right message. The reset link works once. A customer gets 403 on `/products` |
| **B2. Staff and customers** | Admin-only staff creation. Customer CRUD (staff and admin) | Staff cannot call the users endpoints. Staff never see the Users menu |
| **B3. Products and variants** | Product CRUD with an inline variant editor (attribute, value, extra price) | The Odoo variant adds 560 in the line picker |
| **B4. Plans** | Plan CRUD with period, minimum quantity, availability dates and the four switches | Plans outside their dates cannot be picked for a new subscription |
| **B5. Quotation templates** | Template CRUD with lines and validity in days | A new subscription from a template pre-fills plan and lines |
| **B6. Subscriptions** | List (server-paginated, filtered), form with lines using `POST /api/pricing/preview`, auto number, state machine in `services/subscriptions.py` including Paused, action buttons shown only when the plan allows. Becoming Active sets `next_invoice_date` | Illegal transitions are refused. The state is visible in the list and the detail view |
| **B7. Lifecycle** | Daily job closes expired subscriptions when the plan auto-closes, expires stale quotations. Renew creates the next term. `POST /api/subscriptions/run-lifecycle` | The job is idempotent |
| **B8. Portal subscriptions** | `/portal/subscriptions` endpoints and page, with pause, close or renew when the plan allows | A customer can never load another customer's records |
| **B9. Polish** | Empty and loading states, responsive layout, debounced search (about 300 ms), pagination on every list, lint and build clean | `npm run build` and `npm run lint` pass |

---

## 7. Timeline (8-hour round)

Hours from the start. Phase 0 is already done. If the 24-hour final applies, scale each block up by about 3.

| Hours | Person A: Money side | Person B: Sell side | Checkpoint |
|-------|----------------------|---------------------|------------|
| 0 to 0.5 | Together: review the schema, agree the API contract | | **Contract frozen** |
| 0.5 to 2 | A1 taxes, A2 discounts, start the seed | B1 auth and roles, B2 staff and customers | Both features click through in the UI. **Seed ready by 2** |
| 2 to 3.5 | A3 invoice generation (with concurrency tests) | B3 products, B4 plans, B5 templates | Create a product with the Odoo variant, a plan and a template in the UI |
| 3.5 to 5 | A4 billing run and page, A5 invoices | B6 subscriptions and the state machine | **First end-to-end run at about 5:** template, subscription Active, billing run, invoice |
| 5 to 6.5 | A6 payments, A7 dashboard, A8 portal invoices | B7 lifecycle, B8 portal subscriptions, validation polish | Payments, dashboard and both portal pages work. **Feature freeze at 6.5** |
| 6.5 to 7.25 | A9 performance and the big seed. Cross-test B's features | B9 polish. Cross-test A's features | Everything under 2 seconds |
| 7.25 to 8 | Together: README, clean-clone test, demo rehearsal, submit **before the deadline** | | The demo script in section 10 runs cleanly |

**Rebalancing:** if A is ahead, A takes B7 or B8. If B is behind at hour 4, A takes B5 (templates). Trim polish before features.

**If time runs short, cut in this order:** portal self-service actions, send-by-email polish, extra dashboard filters, the revenue chart. Never cut the Billing Run, the invoice screens, roles or validation.

---

## 8. Risks

| Risk | Mitigation |
|------|-----------|
| A blocked waiting for subscriptions | A builds and tests billing against seeded Active subscriptions. B's state machine only has to set `next_invoice_date` |
| Double billing under concurrency | DB `UNIQUE(subscription_id, period_start)`, one transaction, row locks. On `IntegrityError` return the existing invoice |
| Invoice numbers clash or gap | The `Sequence` table is updated inside the invoice transaction, so a rollback leaves no gap |
| Slow dashboard with thousands of rows | SQL aggregates, indexes, server-side pagination |
| Screens show different totals from the server | Forms always call `POST /api/pricing/preview` and never re-implement the math |
| Schema merge conflicts | Models and migrations are shared: tell the other person first, one migration per PR |
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
