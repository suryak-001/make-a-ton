# Subscription Management System: Build Plan for 2 People

Source: `Subscription_Management_System.pdf` (Brightloop Software scenario).
Requirements and decisions: **[docs/PRD.md](docs/PRD.md)**. API contract between the two halves: **[docs/API_CONTRACT.md](docs/API_CONTRACT.md)**.

**Sell side** (auth, catalogue, subscriptions, portal subscriptions) and **Money side** (taxes, discounts, billing, invoices, payments, reports, portal invoices). Each side is built by one person, who builds their features end to end, backend and frontend. Steps are numbered **S1 to S9** (sell side) and **M1 to M9** (money side).

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

| | **Sell side** | **Money side** |
|---|---|---|
| Scenes | R1 sign up, R2 roles, R3 products, R4 plans, R5 templates, R6 subscriptions | R7 billing day, R8 taxes, R9 discounts, R10 payments, R11 reports |
| Hard part | Subscription state machine, quote builder, role-guarded screens | Billing engine, discount limits under concurrency, report performance |
| Volume | More screens, more routine CRUD | Fewer screens, harder logic |
| Also owns | Customers, portal subscriptions page | Portal invoices page |

**Who owns which files** (to avoid merge conflicts, each feature lives in its own files)
```
backend/app/routers/<feature>.py, backend/app/services/<feature>.py     the feature's owner
frontend/src/pages/<route>/index.tsx                                      the feature's owner (auto-registered by routes.tsx)
backend/tests/test_<feature>.py                                           the feature's owner
Money side (B): taxes, discounts, invoices, payments, reports, pricing, portal_invoices, services/billing.py, services/discounts.py
Sell side (A): users, customers, products, plans, quotation_templates, subscriptions, portal_subscriptions, services/subscriptions.py, core/* and routers/auth.py
```
**Shared, change only after telling the other person:** `backend/app/models/*` (one Alembic migration per PR), `backend/app/seed.py` (the money side edits the money sections, the sell side edits the sell sections), `frontend/src/nav.ts`, `frontend/src/components/ui.tsx` (add new primitives, do not restyle existing ones), `frontend/src/lib/api.ts`.

**Rules**
1. The API contract in **docs/API_CONTRACT.md** is frozen at kick-off. Each owner publishes their own endpoints, and the other consumes them. A change needs both people to agree in chat.
2. Short branches, small pull requests, merge to `main` at least every hour. Rebase on `main` before a PR. No force pushes.
3. Commit from your own account with messages that say why. Never commit secrets (`.env` stays ignored).
4. A feature is done only when its API, its screen and its tests all work. Say "done" only after you have clicked through it.
5. **Cross-explain.** After each checkpoint, each person spends about 5 minutes walking the other through their code, especially billing and the state machine. Anyone may be asked about any file at the desk.
6. **Cross-test.** In the harden phase each person tries to break the other's features.

**The one dependency between you:** billing needs Active subscriptions. The money side builds and tests billing against seeded Active subscriptions, so it never waits. The sell side's state machine must set `next_invoice_date` when a subscription becomes Active (the handoff contract in `docs/API_CONTRACT.md` and the stubs in `backend/app/services/`).

---

## 4. Phase 0 (done)

Scaffolded 2026-10-31: skeleton, full schema and first Alembic migration, login and logout with role guards on API and UI, nav shell with placeholder pages, contract stubs, a tested pricing engine (also at `POST /api/pricing/preview`), and the seed script. See `README.md`.

Still to do together at kick-off: review the schema once and agree the API contract.

---

## 4b. Status

**Both sides are built and merged to `main`.**
- **Sell side:** auth with signup and password reset, staff, customers, products and variants, plans, quotation templates, subscriptions with the state machine and history, the lifecycle job, and portal subscriptions.
- **Money side:** taxes, discounts, invoice generation, the billing run, invoices (confirm, cancel, send, print), payments, reports and the dashboard, and portal invoices.
- 127 backend tests pass, and the frontend builds and lints clean. The money-side screens (taxes, discounts, billing run, invoices, payments, reports) have been clicked through in a browser against the 5,000-subscription seed. The sell side has not been clicked through end to end yet.

Decisions the build follows (details in `docs/PRD.md`): quote validity starts when the quote is sent, minimum quantity is checked per line, every state change writes a history event, portal pause, close and renew is core, and the invoice number is assigned at Confirm.

**Closed since the money-side review:**
- Report filters: date range, plan, customer and status now reach the summary, the revenue chart and the overdue list, and every figure is a two-decimal amount.
- Discounts: tests for automatic application, expiry, an exhausted limit and 20 concurrent uses of a limit-5 discount (exactly 5 apply). The UI picks several products or searches subscriptions, and rules can be edited and deleted. A subscription-level discount now lowers the tax too.
- Performance: the `--big` seed creates invoices and payments, and `EXPLAIN` plus timings are recorded in `docs/API_CONTRACT.md`. Payments are paginated and filterable.
- Invoices: customer and date filters, a Billing Run page whose counts add up, and the server tells the UI which actions are allowed.

**Open work:**
1. Lifecycle only runs when an admin clicks "Run lifecycle job". Add a scheduled daily run so plans really "close on their own".
2. MRR sums line prices and ignores discounts. The PRD defines it as net of discounts, so the on-screen definition says "before discounts" until this is done.
3. The admin "re-bill" action for a cancelled invoice (PRD FR-23) is not built. A cancelled period is never re-billed automatically.
4. A very large billing run is one request: about 10 ms per invoice, so roughly a minute for 5,700 due periods. Run it in the background if volumes grow.

---

## 5. Money side

Every step ships the API, the screen and tests.

| Step | Deliverable | Done when |
|------|-------------|-----------|
| **M1. Taxes** | Admin-only tax CRUD (API and screen). Taxes apply to subscription lines through the pricing engine | A tax created in the UI changes a quote total |
| **M2. Discounts** | Admin-only discount CRUD with all rules (fixed or percent, minimum purchase or quantity, dates, usage limit, product or subscription scope) and screen | An invalid rule is refused with a field message |
| **M3. Invoice generation** | `generate_invoice_for_period` in `services/billing.py`: snapshot lines, taxes, applicable discounts, `DiscountUsage` with the discount row locked, all in one transaction. Make `Invoice.number` nullable and assign the number from the `Sequence` table at Confirm (M5) | Same period twice returns the existing invoice. Twenty concurrent uses of a limit-5 discount apply exactly 5 times |
| **M4. Billing run and page** | `run_billing` (`<= as_of`, `with_for_update(skip_locked=True)`, catch-up, failures recorded and the run continues) and the **Billing Run page** with live counts that add up, a "Run again" button and an "as of" date | Run three times: count unchanged. Three periods behind gives exactly 3 invoices. The counts add up on screen |
| **M5. Invoices** | List (filters: status, overdue, customer, dates), detail, confirm (assigns the invoice number), cancel, send (email), print page. Every transition is guarded | Illegal actions are refused by the server and hidden or disabled in the UI |
| **M6. Payments** | Record method, amount, date and note against an invoice. Partial allowed, overpayment blocked, auto-mark Paid. Payments list | Outstanding updates immediately and the overdue badge shows |
| **M7. Reports and dashboard** | SQL aggregates for the summary, overdue list and revenue by month, with filters. Dashboard with cards, chart, overdue table and metric definitions in tooltips | Every number comes from `func.sum` and `group_by`. Loads in under 2 seconds |
| **M8. Portal invoices** | `/portal/invoices` endpoints scoped to the signed-in customer, plus the page and print view | Another customer's invoice returns 404 |
| **M9. Performance** | `--big` seed (5,000 subscriptions with invoices and payments), indexes checked with `EXPLAIN`, pagination everywhere | Every page under 2 seconds. Measured and noted for the demo |

---

## 6. Sell side

Every step ships the API, the screen and tests. Pages live in `frontend/src/pages/<route>/index.tsx`.

| Step | Deliverable | Done when |
|------|-------------|-----------|
| **S1. Auth and roles** | Signup (unique email, password policy in `core/security.py`) with live hints, password reset by emailed single-use token (hashed, expires in 1 hour), forgot and reset pages, role shell and Forbidden page. Extend `ApiError` to carry FastAPI's 422 field messages | Weak passwords and duplicate emails show the right message. The reset link works once. A customer gets 403 on `/products` |
| **S2. Staff and customers** | Admin-only staff creation. Customer CRUD (staff and admin) | Staff cannot call the users endpoints. Staff never see the Users menu |
| **S3. Products and variants** | Product CRUD with an inline variant editor (attribute, value, extra price) | The Odoo variant adds 560 in the line picker |
| **S4. Plans** | Plan CRUD with period, minimum quantity, availability dates and the four switches | Plans outside their dates cannot be picked for a new subscription |
| **S5. Quotation templates** | Template CRUD with lines and validity in days | A new subscription from a template pre-fills plan and lines |
| **S6. Subscriptions** | List (server-paginated, filtered), form with lines using `POST /api/pricing/preview`, auto number, state machine in `services/subscriptions.py` including Paused, action buttons shown only when the plan allows. Becoming Active sets `next_invoice_date` | Illegal transitions are refused. The state is visible in the list and the detail view |
| **S7. Lifecycle** | Daily job closes expired subscriptions when the plan auto-closes, expires stale quotations. Renew creates the next term. `POST /api/subscriptions/run-lifecycle` | The job is idempotent |
| **S8. Portal subscriptions** | `/portal/subscriptions` endpoints and page, with pause, close or renew when the plan allows | A customer can never load another customer's records |
| **S9. Polish** | Empty and loading states, responsive layout, debounced search (about 300 ms), pagination on every list, lint and build clean | `npm run build` and `npm run lint` pass |

---

## 7. Timeline (8-hour round)

Hours from the start. Phase 0 is already done. If the 24-hour final applies, scale each block up by about 3.

| Hours | Money side | Sell side | Checkpoint |
|-------|----------------------|---------------------|------------|
| 0 to 0.5 | Together: review the schema, agree the API contract | | **Contract frozen** |
| 0.5 to 2 | M1 taxes, M2 discounts, start the seed | S1 auth and roles, S2 staff and customers | Both features click through in the UI. **Seed ready by 2** |
| 2 to 3.5 | M3 invoice generation (with concurrency tests) | S3 products, S4 plans, S5 templates | Create a product with the Odoo variant, a plan and a template in the UI |
| 3.5 to 5 | M4 billing run and page, M5 invoices | S6 subscriptions and the state machine | **First end-to-end run at about 5:** template, subscription Active, billing run, invoice |
| 5 to 6.5 | M6 payments, M7 dashboard, M8 portal invoices | S7 lifecycle, S8 portal subscriptions, validation polish | Payments, dashboard and both portal pages work. **Feature freeze at 6.5** |
| 6.5 to 7.25 | M9 performance and the big seed. Cross-test the sell side's features | S9 polish. Cross-test the money side's features | Everything under 2 seconds |
| 7.25 to 8 | Together: README, clean-clone test, demo rehearsal, submit **before the deadline** | | The demo script in section 10 runs cleanly |

**Rebalancing:** whoever finishes first takes the next unfinished step from the other side. Trim polish before features.

**If time runs short, cut in this order:** portal self-service actions, send-by-email polish, extra dashboard filters, the revenue chart. Never cut the Billing Run, the invoice screens, roles or validation.

---

## 8. Risks

| Risk | Mitigation |
|------|-----------|
| Money side blocked waiting for subscriptions | The money side builds and tests billing against seeded Active subscriptions. The sell side's state machine only has to set `next_invoice_date` |
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
