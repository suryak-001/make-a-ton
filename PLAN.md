# Subscription Management System: Build Plan for 2 People

Source: `Subscription_Management_System.pdf` (Brightloop Software scenario). Behaviour decisions follow `Brightloop PRD.md` (31 Oct 2026); where this plan and the PRD differ, the PRD wins unless section 1 says otherwise.

---

## 1. What we're building (requirements digest)

One web app that runs a subscription business from start to finish: **catalog → quotation → subscription → invoice → payment → reporting**.

| # | Scene | What it has to do |
|---|-------|-------------------|
| R1 | **Sign up / auth** | Sign up with email and password. Each email can have only one account. Password must be **>8 chars** (so at least 9) with an upper-case letter, a lower-case letter and a special character. Forgot password sends a **reset link by email**. |
| R2 | **Roles** | **Admin** controls everything. **Internal staff** get limited access. **Customers** use a portal and see only their own subscriptions and invoices. **Only the admin can create staff.** |
| R3 | **Products** | Name, type, sales price, cost price, notes. **Variants** with an attribute and an extra price (e.g. Brand = Odoo, **+560**). |
| R4 | **Plans** | Price, billing period (**daily / weekly / monthly / yearly**), min quantity, start and end availability dates. Per-plan flags: **auto-close**, **closable**, **pausable**, **renewable**. |
| R5 | **Quotation templates** | A preset plan with product lines and a **validity in days**. Used to start a subscription quickly. |
| R6 | **Subscriptions** | Auto **number**, customer, plan, start date, expiry date, payment terms. Lines have product, qty, unit price, taxes and amount. Status flow is **Draft → Quotation → Confirmed → Active → Closed**, and the whole team can see it. |
| R7 | **Billing day** | Invoices are generated **in bulk from subscriptions**, with customer, lines, taxes and totals filled in automatically. Each invoice can be confirmed, cancelled, sent or printed. Status flow is **Draft → Confirmed → Paid**. **No double-billing, no skipped periods.** |
| R8 | **Taxes** | The admin defines tax rules, and the system applies them automatically. |
| R9 | **Discounts** | **Admin only.** Fixed or %, with a min purchase or min qty, start and end dates, and a **usage limit**. Applies to specific products or a whole subscription. It appears on the next invoice **automatically** and stops once it expires or runs out. |
| R10 | **Payments** | Record method, amount, date and a note against an invoice. Show paid vs outstanding vs **overdue** at any time. |
| R11 | **Reports** | One dashboard with active subscriptions, revenue, payments, outstanding and overdue amounts, plus filters and a summary. **Every page responds in < 2 s with thousands of subscriptions.** |
| R12 | **Customer portal** | A customer sees only their own subscriptions and invoices, with downloads. Where the plan allows it, they can **pause, close or renew** without emailing anyone. |

### Assumptions where the brief is vague (decided up front so nobody blocks on them)
- **Staff permissions:** staff manage customers, quotations, subscriptions, invoices and payments. They can only *view* products and plans (read-only, because they need them to build a quote; the PRD's "no setup screens" means no create/edit). Taxes, discounts, products, plans and users are **admin-only**.
- **Customer vs user:** a `Customer` record can exist without a login, because sales reps create customers. Public signup **always** creates a `User(role=CUSTOMER)` and a linked `Customer`; only the admin creates staff.
- **Access errors:** a signed-in user hitting a screen or API their role doesn't allow gets **403**. A customer requesting another customer's record gets **404**, so existence isn't leaked.
- **Email and reset:** emails are unique case-insensitively (stored lower-cased). Forgot-password always returns the same response whether or not the email exists. Reset tokens are single-use, short-lived and stored hashed.
- **Paused:** `PAUSED` is reachable only from `ACTIVE`, and only when `plan.pausable`. A paused subscription generates no invoices. Resuming returns it to `ACTIVE`.
- **Plan rules:** a plan outside its availability dates can't be picked for a new subscription, and a line quantity below `plan.minQuantity` is rejected (server-side).
- **Quote validity:** the clock starts when the quote is **sent** (Draft → Quotation): `quotationValidUntil = sentDate + validityDays`. A stale quotation is expired by the lifecycle job.
- **Invoice states:** Draft → Confirmed → Paid, plus **Cancelled**. Partial payments leave the invoice Confirmed with an outstanding balance. It becomes Paid once `amountPaid >= total`.
- **Invoice numbering and immutability:** the invoice number (`INV-2026-00001`) is assigned at **Confirm**, not at creation, so cancelled drafts leave no gaps. A Confirmed invoice is never edited; cancel it instead. Invoice lines snapshot product name, price, tax rate and discount, so later catalogue edits never change old invoices.
- **Overdue** means `status = CONFIRMED`, `dueDate < today` and an outstanding balance > 0. `dueDate = invoiceDate + paymentTermDays`. It is a derived badge, never a stored state.
- **Billing dates:** period *n* starts at `add_period(startDate, period, n)`, always computed from the **original start date**, never by adding one period to the previous date. A 31 Jan monthly subscription bills 28 Feb, 31 Mar, 30 Apr.
- **Discounts:** one use is counted per invoice the discount appears on. The limit check and the count are a single atomic step. At most one product-level and one subscription-level discount apply per invoice, and a discount never takes a line below zero.
- **Payments:** partial payments are allowed, overpayment is rejected, and a payment is recorded against exactly one invoice.
- **Dashboard definitions:** *Invoiced* (confirmed/paid invoice totals) and *Collected* (payments received) are shown separately, because the brief doesn't define "revenue". **MRR** is monthly-equivalent, net of discounts, excluding tax, and the definition is shown on screen.
- **Money** is stored as `Decimal` / `Numeric(12,2)` (exact, never float). The PRD suggests whole minor units; we keep `Decimal` because the pricing engine and tests are already built on it. Every calculation goes through one pricing module.
- **Print** is a print-friendly HTML page (browser → PDF). **Send** emails the customer a link to it, or a PDF if time allows.
- **Out of scope** (per the PRD): multiple companies/tenants, payment gateway, proration, mobile app, GST print format, automatic reminder emails, microservices.

---

## 2. Stack (Python + React)

| Layer | Choice | Why |
|-------|--------|-----|
| API | **FastAPI** (Python 3.13, managed by `uv`) | Typed request/response models, automatic OpenAPI docs at `/docs`, dependency-based auth |
| DB | **PostgreSQL + SQLAlchemy 2 + Alembic** | Real transactions and unique constraints (needed for the no-double-billing rule); migrations in `backend/alembic/versions` |
| Money | `Decimal` end to end, `Numeric(12,2)` in the DB | No float rounding errors |
| Auth | bcrypt + signed `HttpOnly` session cookie (`itsdangerous`) | Full control of password rules, roles and reset tokens |
| Email | `smtplib`; printed to the server console in dev | Reset links and invoice emails (swap in Mailtrap or Resend later) |
| Frontend | **React 19 + TypeScript + Vite** | Fast dev loop |
| UI | Tailwind 4 | Small primitives in `frontend/src/components/ui.tsx` |
| Routing / data | React Router 8 + TanStack Query | Role-guarded routes, cached server data |
| Tests | pytest (backend), `tsc` + oxlint (frontend) | |

The browser only talks to the Vite dev server, which proxies `/api` to FastAPI. The session cookie is therefore same-origin and no CORS setup is needed.

---

## 3. How we split the work: vertical slices, not frontend/backend

Each person owns full features end-to-end (DB → API → UI). That way neither of you waits on the other for endpoints. The only thing you share is the **data model**, which you write together in Phase 0.

### 👤 Person A: "Identity, Catalog & Subscriptions" (the *sell* side)
R1, R2, R3, R4, R5, R6, R12 (portal subscriptions and self-service actions)

### 👤 Person B: "Billing, Money & Insights" (the *collect* side)
R7, R8, R9, R10, R11 + the shared pricing engine + portal invoices

Rough load: A has more screens, while B has the harder logic (billing engine, discounts, reports performance). That balances out.

---

## 4. Phase 0: Together (first ~2 hours). **Do not skip.**

> ✅ **Scaffolded (2026-10-31, Python + React).** Skeleton, full schema plus first Alembic migration, auth with real login and logout, role guards on both API and UI, nav shell with placeholder pages, contract stubs, a working and tested pricing engine (also exposed at `POST /api/pricing/preview`), and the seed are all in place. See README.md. Still to do together: review the schema and set up the deploy pipeline.

Pair on this, because it is what makes everything after it parallel.

1. **Repo skeleton**: FastAPI + Alembic backend, Vite + React + Tailwind frontend, `.env.example`, deploy pipeline. *(A drives, B reviews)*
2. **Full SQLAlchemy models** (section 7) written and migrated with Alembic. Both of you agree on every enum and relation.
3. **Shared contracts** (section 6): function signatures stubbed with `raise NotImplementedError("TODO")` or mock returns.
4. **Layout and nav shell**: sidebar with every menu item, role-based visibility, empty pages.
5. **Seed script skeleton**: 1 admin, 1 staff, 3 customers, a few products, plans and taxes. Each person extends their own section later.
6. **Folder ownership** agreed (section 5). Branch-per-feature, small PRs, merge to `main` several times a day.

**Exit criteria:** the backend (`uvicorn`) and frontend (`npm run dev`) both start, the DB is migrated and seeded, everyone can log in as a hard-coded admin (stub), and all nav links resolve to placeholder pages.

---

## 5. Folder ownership (avoids merge conflicts)

```
backend/app/models/*.py            SHARED: change only after pinging the other person; one Alembic migration per PR
backend/app/seed.py                SHARED: A edits the catalog/subscription sections, B edits the rules/billing sections
backend/app/core/*                 A  (password policy, session cookie, get_current_user, require_roles)
backend/app/routers/auth.py        A  (login/logout/me done; signup, forgot/reset password to do)
backend/app/routers/{users,customers,products,plans,quotation_templates,subscriptions,portal_subscriptions}.py   A
backend/app/services/subscriptions.py   A  (state machine, lifecycle job)
backend/app/services/{pricing,billing,discounts}.py   B
backend/app/routers/{taxes,discounts,invoices,payments,reports,pricing,portal_invoices}.py   B
backend/app/services/{dates,sequence,mail}.py   shared helpers, tell the other before changing behaviour
backend/tests/                     each person adds test_<feature>.py files for their own track
frontend/src/pages/<route>/index.tsx   drop-in pages, auto-registered by routes.tsx (no routing edits)
    A: users, customers, products, plans, quotation-templates, subscriptions, portal/subscriptions
    B: dashboard, taxes, discounts, invoices, payments, reports, portal/invoices
frontend/src/auth/*  frontend/src/lib/api.ts   A  (session, route guard, fetch wrapper)
frontend/src/nav.ts                SHARED: only to add or change menu entries
frontend/src/components/ui.tsx     shared primitives: add new ones, don't restyle existing ones without asking
```

---

## 6. Shared contracts (agreed in Phase 0, stubbed immediately)

```python
# backend/app/core/deps.py — owned by A (done)
CurrentUser                      # FastAPI dependency: the signed-in User, or 401
require_roles(*roles: Role)      # dependency factory: 401 if signed out, 403 if the role isn't allowed
AdminUser, StaffUser, CustomerUser   # ready-made type aliases (StaffUser = admin or staff)
# B puts AdminUser on taxes/discounts routes from day one.

# backend/app/services/pricing.py — owned by B (done, tested)
compute_line(unit_price, quantity, variant_extra=0, taxes=[], discount=None) -> LineResult
    # (unit_price, subtotal, discount_amount, tax_amount, total), all Decimal
compute_totals(lines) -> Totals
# POST /api/pricing/preview exposes it, so forms show the same numbers the backend stores.
# The frontend never re-implements pricing math.

# backend/app/services/billing.py — owned by B
generate_invoice_for_period(db, subscription_id, period_start) -> Invoice   # idempotent
run_billing(db, as_of: date) -> BillingRunResult(created, skipped, errors)

# backend/app/services/subscriptions.py — owned by A
transition_subscription(db, subscription_id, to: SubscriptionStatus) -> Subscription  # enforces the state machine
# On -> ACTIVE: sets next_invoice_date = start_date. B's billing run picks it up from there.
# Every call writes a SubscriptionEvent (from, to, actor, reason). The portal calls it too, with the same plan-flag checks.

# backend/app/services/invoices.py — owned by B
confirm_invoice(db, invoice_id) -> Invoice    # assigns the INV- number; Draft only
cancel_invoice(db, invoice_id) -> Invoice     # Draft or Confirmed with no payments
```

**Handoff contract between tracks:** A guarantees that an `ACTIVE` subscription has a valid `next_invoice_date`, `payment_term_days` and at least one line. B guarantees that `run_billing` never creates two invoices for the same `(subscription_id, period_start)`, and that the invoice and the advanced `next_invoice_date` are saved **in the same transaction**. The next date is `add_period(start_date, period, n)` from the original start date, so month-end subscriptions don't drift. A `PAUSED` subscription is never billed.

---

## 7. Data model (implemented in `backend/app/models/`; names below are the original sketch in camelCase, the code uses snake_case)

```
User              id, email UNIQUE, passwordHash, name, role(ADMIN|STAFF|CUSTOMER), createdAt
PasswordResetToken id, userId, tokenHash, expiresAt, usedAt
Customer          id, name, email, phone, address, userId? UNIQUE (portal login)

Product           id, name, type(SERVICE|GOODS), salesPrice, costPrice, notes, active
ProductVariant    id, productId, attribute ("Brand"), value ("Odoo"), extraPrice (560)

Plan              id, name, price, billingPeriod(DAILY|WEEKLY|MONTHLY|YEARLY), minQuantity,
                  availableFrom, availableTo, autoClose, closable, pausable, renewable

QuotationTemplate id, name, planId, validityDays, notes
QuotationTemplateLine id, templateId, productId, variantId?, quantity

Subscription      id, number UNIQUE ("SUB-00001"), customerId, planId,
                  status(DRAFT|QUOTATION|CONFIRMED|ACTIVE|PAUSED|CLOSED),
                  startDate, expiryDate, paymentTermDays, quotationValidUntil?,
                  nextInvoiceDate?, createdById, createdAt
                  INDEX(status), INDEX(customerId), INDEX(status,nextInvoiceDate)
SubscriptionLine  id, subscriptionId, productId, variantId?, quantity, unitPrice, amount
SubscriptionLineTax (M2M line ↔ Tax)
SubscriptionEvent id, subscriptionId, fromStatus?, toStatus, reason?, actorId, createdAt   (state history + close reason)

Tax               id, name, kind(PERCENT|FIXED), rate, active
Discount          id, name, kind(PERCENT|FIXED), value, minPurchase?, minQuantity?,
                  startDate, endDate, usageLimit?, usedCount, scope(PRODUCT|SUBSCRIPTION), active
DiscountProduct   (M2M discount ↔ product, for scope=PRODUCT)
DiscountSubscription (M2M discount ↔ subscription, for scope=SUBSCRIPTION)

Invoice           id, number? UNIQUE ("INV-2026-00001", NULL until Confirm), subscriptionId, customerId,
                  status(DRAFT|CONFIRMED|PAID|CANCELLED), periodStart, periodEnd,
                  invoiceDate, dueDate, subtotal, discountTotal, taxTotal, total, amountPaid,
                  sentAt?, createdAt
                  UNIQUE(subscriptionId, periodStart)   ← the "never bill twice" guarantee
                  INDEX(status, dueDate), INDEX(customerId), INDEX(invoiceDate)
InvoiceLine       id, invoiceId, description, productId, productName, quantity, unitPrice,
                  discountAmount, taxRate, taxAmount, total   (snapshot: later catalog edits don't change old invoices)
DiscountUsage     id, discountId, invoiceId   UNIQUE(discountId, invoiceId)   (one use per invoice)

Payment           id, invoiceId, method(CASH|BANK_TRANSFER|CARD|UPI|CHEQUE|OTHER),
                  amount, paymentDate, note, recordedById
                  INDEX(paymentDate)
Sequence          name PK, next   (atomic numbering for SUB / INV)
```

---

## 8. Track A: Identity, Catalog & Subscriptions

| Step | Deliverable | Done when |
|------|-------------|-----------|
| **A1. Auth** | Signup (email unique case-insensitively, password policy in `core/security.py` (`password_problems`), validated on client and server), login, logout, sessions, `require_roles`, frontend route guard | An 8-character password is rejected and a 9-character one that meets the rules is accepted. A duplicate email (any casing) is rejected, and a customer gets 403 on `/products` |
| **A2. Password reset** | Forgot form → hashed single-use token (expires in 1 hour) → emailed link → reset page. The response is identical whether or not the email exists | Link arrives in Ethereal/Mailtrap, works once, then expires. An unknown email gets the same response as a known one |
| **A3. Users & customers** | Admin-only "Add staff" page. Customer CRUD (staff and admin) | Staff can't see the Users menu |
| **A4. Products + variants** | Product CRUD with an inline variant editor (attribute, value, extra price) | "Odoo" variant adds 560 to price in the line picker |
| **A5. Plans** | Plan CRUD with period, min qty, availability dates and the 4 behaviour flags | Plans outside their availability window can't be picked for new subscriptions |
| **A6. Quotation templates** | Template CRUD with lines and validity days | "New subscription from template" pre-fills plan and lines. Sending the quote sets `quotationValidUntil = sentDate + validityDays` |
| **A7. Subscriptions** | List (server-paginated, filter by status/customer/plan), form with lines (uses `POST /api/pricing/preview` from B), auto number, quantity below `plan.minQuantity` rejected, **state machine** (one server function) with action buttons (Send quotation / Confirm / Activate / Pause / Renew / Close), each button only shown when the plan allows it, and a state-history timeline from `SubscriptionEvent` | Illegal transitions are rejected server-side. The status badge is visible in the list and detail views. Every state in the flow can be walked through |
| **A8. Lifecycle automation** | Daily job: close expired subs when `plan.auto_close`, expire stale quotations. Renew creates the next term | The job is idempotent and can be triggered from a button or `POST /api/subscriptions/run-lifecycle` |
| **A9. Customer portal** | `/portal`: my subscriptions, detail and profile. **Self-service Pause / Close / Renew**, shown only where the plan flags allow, going through `transition_subscription`. Hosts B's invoices page | A customer can never load another customer's records (404, checked server-side). A non-pausable plan offers no Pause button and the API rejects it too |

---

## 9. Track B: Billing, Money & Insights

| Step | Deliverable | Done when |
|------|-------------|-----------|
| **B1. Pricing engine (do first, ~2h)** | `services/pricing.py`: line math, % and fixed taxes, discount application, rounding. **Unit tests** *(done in Phase 0)* | A can import it. Tests cover variant extra, multi-tax, fixed vs % discount |
| **B2. Taxes** | Admin-only tax CRUD. Default tax per product (optional) | Taxes auto-apply to subscription lines |
| **B3. Discounts** | Admin-only discount CRUD with all rules (fixed/%, min purchase/qty, dates, usage limit, product vs subscription scope). Stacking: at most one product-level and one subscription-level discount per invoice, and a line never goes below zero | `findApplicableDiscounts(subscription, date)` returns only valid discounts that haven't hit their limit |
| **B4. Invoice generation** | `generate_invoice_for_period`: snapshot lines (name, price, tax rate), apply taxes and auto-discounts, record `DiscountUsage`, all **in one transaction**. The use is claimed atomically: `UPDATE discount SET used_count = used_count + 1 WHERE id = :id AND (usage_limit IS NULL OR used_count < usage_limit)`; zero rows updated means the discount is skipped | Running it twice for the same period returns the existing invoice and creates no duplicate. A discount with limit 5 hit by 20 simultaneous runs is applied exactly 5 times |
| **B5. Billing run** | `run_billing(db, as_of)`: for every ACTIVE sub with `nextInvoiceDate <= asOf`, loop period by period (**catch-up, so nothing is skipped**). Each period's invoice and the advanced `nextInvoiceDate` commit **together**. Period starts come from `add_period(startDate, period, n)`. "Run billing now" admin button + `POST /api/invoices/run-billing` | Run it 3× in a row and the invoice count stays the same. A sub 3 months behind gets exactly 3 invoices. 500 due subscriptions give 500 invoices on the first run and 0 on the second. A 31 Jan monthly sub bills 28 Feb, 31 Mar, 30 Apr |
| **B6. Invoice UI** | List (filter by status/customer/date/overdue), detail, actions: **Confirm** (assigns the `INV-` number) **/ Cancel / Send (email) / Print** (print-CSS page), status badges. Confirmed invoices are read-only | Every transition is guarded (you can't confirm a cancelled invoice, edit a confirmed one, etc.). Cancelled drafts leave no gap in the numbering |
| **B7. Payments** | Record payment (method, amount, date, note) from the invoice page. Payments list. Auto-mark Paid when fully paid. Block overpayment | Outstanding balance updates immediately. Overdue badge shows when past due |
| **B8. Reports dashboard** | KPI cards: active subs, MRR, **Invoiced** and **Collected** (shown separately), outstanding, overdue (count and amount). The MRR definition is shown on screen. Revenue-by-month chart. Overdue invoice table with aging buckets (1-30, 31-60, 60+ days) if time allows. Filters: date range, plan, customer, status | All numbers come from SQL aggregates (SQLAlchemy `func.sum`/`group_by`), never by loading rows into JS |
| **B9. Portal invoices** | `/portal/invoices`: my invoices, status, print/download | Customer sees only their own |
| **B10. Performance** | Seed **5,000 subscriptions / 50,000 invoices / 30,000 payments**. Server-side pagination everywhere. Check indexes with `EXPLAIN` | Every page under 2 s (measure and note the result for the demo) |

---

## 10. Timeline and sync points

Durations assume a ~24-hour hackathon. Scale them proportionally if yours is different.

| Phase | Time | Person A | Person B | Sync |
|-------|------|----------|----------|------|
| **0** Foundation | 0–2h | *together*: skeleton, schema, contracts, nav, seed | | ✅ Schema frozen |
| **1** Core | 2–10h | A1 → A2 → A3 → A4 → A5 | B1 (pricing, hand to A) → B2 → B3 → B4 | **Checkpoint at ~6h:** A finishes signup/reset; B ships `/api/pricing/preview` (already done) |
| **2** Flow | 10–16h | A6 → A7 (subscriptions + state machine) | B5 → B6 → B7 | **Checkpoint at ~14h:** first end-to-end run: template → sub → activate → billing run → invoice → payment |
| **3** Complete | 16–20h | A8 → A9 portal | B8 reports → B9 portal invoices | |
| **4** Harden | 20–22h | Role/permission audit, validation messages, empty states | B10 big seed + perf pass | **Cross-test each other's tracks** |
| **5** Demo | 22–24h | *together*: demo seed data, script rehearsal, README, deploy | | |

**Daily rituals:** a 5-minute sync at each checkpoint. Announce schema changes in chat before pushing. Rebase on `main` before each PR.

---

## 11. Risks and how we handle them

| Risk | Mitigation |
|------|-----------|
| B blocked waiting for A's subscriptions | The schema is frozen in Phase 0. B seeds ACTIVE subscriptions directly and builds the billing engine against seed data |
| A blocked waiting for pricing | The pricing engine and `POST /api/pricing/preview` already exist (done in Phase 0) |
| Double-billing under concurrency | DB `UNIQUE(subscriptionId, periodStart)` + transaction. Catch the unique violation and return the existing invoice |
| Discount limit exceeded under concurrency | Atomic conditional `UPDATE … WHERE used_count < usage_limit` plus `UNIQUE(discountId, invoiceId)`. Never read-then-write in Python |
| Month-end drift (31 Jan → 28 Feb → 28 Mar…) | Always `add_period(start_date, period, n)` from the original start date, never previous date + 1 period |
| Crash between invoice and next date | Invoice insert and `next_invoice_date` update in one transaction |
| Invoice numbers clash or leave gaps | Number assigned at Confirm only, via the `Sequence` table updated with `INSERT … ON CONFLICT DO UPDATE … RETURNING` (`services/sequence.py`) |
| Slow dashboard with thousands of rows | Aggregate in SQL, add indexes (section 7), paginate, cache KPI queries for 60 s if needed |
| Schema merge conflicts | One migration per PR, ping before editing `backend/app/models` |
| Scope creep | Section 12's "nice-to-haves" only after the end-to-end demo works |

---

## 12. Nice-to-haves (only if ahead of schedule)
- PDF invoice attachment on Send
- Audit log / activity timeline on invoices (subscriptions already have `SubscriptionEvent`)
- MRR churn / growth chart, CSV export
- Optional AI helper, switched off by default: "quote from a sentence" proposes a draft quotation checked against the real catalogue, saved only after a human confirms. The app must work fully without it.

**Out of scope (per the PRD, do not build):** automatic reminder emails (dunning), proration, online payment / payment gateway, multi-tenant, mobile app, GST print format, microservices. Portal self-service pause/close/renew is **core** (A9), not a nice-to-have.

---

## 13. Demo script (maps 1:1 to the brief's scenes)

1. **Sign up** a new customer → show password rules, duplicate email rejection, reset-email link.
2. **Admin** adds staff. Show that staff can't open Discounts and the customer portal is isolated.
3. **Launch a plan**: create a product with the Odoo variant (+560), create a monthly plan with auto-close.
4. **Quote → subscription**: staff picks a quotation template → Draft → Quotation → Confirmed → Active.
5. **Discount**: admin creates "10% off for ≥10 seats, max 5 uses".
6. **Billing day**: click *Run billing* → hundreds of invoices appear, with the discount applied automatically. Click it again → **0 new invoices**.
7. **Money comes in**: record a partial payment, then the rest → invoice becomes Paid. Show the overdue list.
8. **Customer self-service**: sign in as the customer, pause a pausable subscription from the portal, and show that a non-pausable plan offers no Pause button.
9. **Finance lead**: open the dashboard with 5k subscriptions loaded, apply filters, point at the < 2 s load time and the on-screen MRR definition.

---

## 14. Acceptance checks (from the PRD; these are the test list)

1. Signup rejects a duplicate email and an 8-character password; accepts a 9-character one that meets the rules.
2. A staff user cannot open admin screens or create staff. A customer cannot read another customer's invoice (404).
3. Choosing the Odoo brand adds 560 to the price.
4. A template creates a quote with correct lines and an expiry date.
5. A subscription can be walked through every allowed state, and illegal moves are rejected.
6. A billing run over 500 due subscriptions creates 500 invoices. A second run creates 0. A skipped day is caught up on the next run.
7. A discount with limit 5 and 20 simultaneous uses is applied exactly 5 times, and appears on the next invoice with no manual step.
8. Recording payments moves invoices to Paid and updates the dashboard.
9. The dashboard and invoice list load under 2 seconds with 5,000 seeded subscriptions.

## 15. Work needed on the existing scaffold (from the PRD alignment)

- [ ] Alembic migration: `invoice.number` nullable (assigned at Confirm); add `invoice_line.product_name` and `tax_rate`; add `subscription_event`; add `UNIQUE(discount_id, invoice_id)` on `discount_usage`.
- [ ] Billing: compute period starts with `add_period(start_date, period, n)` from the original start date, and commit invoice + `next_invoice_date` together.
- [ ] Discounts: atomic conditional `used_count` increment, one-per-level stacking, never below zero.
- [ ] Portal: pause / close / renew endpoints and buttons gated by plan flags; 404 for other customers' records.
- [ ] Auth: identical forgot-password response for known and unknown emails (emails are already stored lower-cased).
- [ ] Dashboard: separate Invoiced and Collected, MRR definition on screen.
