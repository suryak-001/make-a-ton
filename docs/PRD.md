# Brightloop Subscription Management System: Product Requirements

Source: the hackathon problem statement (`Subscription_Management_System.pdf` in the repo root).
Items marked **(decision)** are choices the brief leaves open. They are fixed here so nobody blocks on them. Put them in the README.

## 1. Problem
Brightloop Software sells software on subscription. Subscriptions live in a spreadsheet, renewals are remembered by whoever notices, invoices are typed by hand, payments are matched by scrolling bank statements, and revenue reports are built by hand each quarter. Renewals are missed, invoices go out wrong, and nobody knows recurring revenue.

## 2. Goal and scope
One system for **one company (Brightloop)** that runs the full subscription life: products and plans, quotes, subscriptions, automatic invoicing, discounts, payments and revenue reporting. It is not a multi-company SaaS. Company name, currency and tax rules live in settings so it could be extended.

**Success:** one billing month runs end to end with no hand-typed invoice, nothing is billed twice or skipped, and the finance lead answers "how many active, how much came in, how much is owed, what is overdue" from one page that loads in under 2 seconds with thousands of subscriptions.

## 3. Stack
FastAPI, SQLAlchemy 2, Alembic and PostgreSQL on the backend. React 19, TypeScript, Vite, Tailwind 4, React Router and TanStack Query on the frontend. Details and setup are in `README.md`. Money is `Decimal(12,2)` in the database and **strings** in JSON (for example `"560.00"`), so no float ever touches an amount.

## 4. Users and permissions
| Role | Can do |
|---|---|
| Admin | Everything. Only role that can add staff, create discount rules, and manage products, plans, taxes |
| Staff | Customers, quotes, subscriptions, invoices, payments, Billing Run. Read-only on products and plans. No setup screens, no staff creation |
| Customer | Own subscriptions and invoices only, through a portal |

Permissions are enforced on the server for every request. A customer asking for another customer's record gets a 404.

## 5. Functional requirements

### 5.1 Accounts and access
- FR-1 Sign up with email and password. One account per email, compared case-insensitively.
- FR-2 Password at least 9 characters ("more than eight"), with an uppercase letter, a lowercase letter and a special character. Validated on client and server.
- FR-3 Forgot password sends a reset link to the registered email. Token is single-use, short-lived and stored hashed. The response never reveals whether the email exists. In development, mail prints to the server console.
- FR-4 Public signup always creates a Customer. Only the Admin creates Staff.
- FR-5 Role-based menus (usability) and server-side permission checks on every endpoint (security).

### 5.2 Products and variants (Admin)
- FR-6 Product: name, type, sales price, cost price, notes.
- FR-7 Variants by attribute (for example brand) with a price add-on. Odoo brand adds 560. Variant price = product price + add-on.

### 5.3 Plans (Admin)
- FR-8 Plan: price, billing period (daily, weekly, monthly, yearly), minimum quantity, available-from and available-to dates.
- FR-9 Per-plan switches: closes automatically when it ends, can be closed early, can be paused, can be renewed.
- FR-10 A plan outside its dates cannot be chosen for a new subscription. A quantity below the minimum is rejected.

### 5.4 Quotation templates and subscriptions
- FR-11 Quotation template: plan, product lines, validity in days. A quote started from a template copies its lines. Expiry = sent date + validity days.
- FR-12 Subscription: unique number, customer, plan, start date, expiry date, payment terms, and lines (product, quantity, unit price, taxes, amount).
- FR-13 States: Draft → Quotation → Confirmed → Active → Closed. Everyone on the team sees the current state.
- FR-14 **(decision)** Add **Paused**. Reachable only from Active and only if the plan allows it. A paused subscription is not billed. On resume, billing continues from the resume date, so paused periods are not charged.
- FR-15 One server function validates every transition. Illegal moves are rejected.
- FR-16 Plans that close automatically move their subscriptions to Closed at expiry. Renewable plans offer a Renew action.

### 5.5 Billing and invoices
- FR-17 A Billing Run creates one invoice per due Active subscription, with customer, lines, taxes and totals filled in.
- FR-18 **Nothing billed twice, nothing skipped.**
  - A unique constraint on (subscription, period start) in the database (`uq_invoice_subscription_period`). This is the guarantee.
  - The invoice is created and the subscription's `next_invoice_date` advances in the same transaction.
  - Due rows are selected with `next_invoice_date <= as_of`, so a missed run is caught up on the next run.
  - Due rows are locked with `with_for_update(skip_locked=True)` so two workers don't take the same row.
  - On an `IntegrityError` the transaction rolls back and the existing invoice is returned.
  - A subscription that fails is recorded with the reason and the rest of the run continues. A failed row stays due, so it is retried.
  - Running again creates 0 invoices.
- FR-19 Daily, weekly, monthly and yearly all work. Dates are computed from the original start date, so a 31 Jan monthly subscription bills 28 Feb, 31 Mar, 30 Apr.
- FR-20 Taxes come from Admin-set rules and are calculated automatically through the shared pricing module. Tax is computed per line and the invoice tax is the sum of the lines.
- FR-21 Invoice states: Draft → Confirmed → Paid, plus Cancelled. Staff can confirm, cancel, send (email) and print (print-friendly page).
- FR-22 The invoice number comes from the `Sequence` table inside the same transaction as the invoice, so a rolled-back run leaves no gap. Lines store a snapshot of product, price and tax, so later catalogue changes do not alter old invoices. Confirmed invoices are not edited, only cancelled.
- FR-23 **(decision)** A cancelled invoice frees its period only through an explicit admin "re-bill" action. The Billing Run never rebills a cancelled period on its own.

### 5.6 Discounts (Admin only)
- FR-24 Rule: fixed amount or percentage; minimum purchase or minimum quantity; start and end dates; usage limit.
- FR-25 Applies to specific products or to whole subscriptions.
- FR-26 An eligible discount appears on the next invoice automatically. It stops when it expires or the limit is used up.
- FR-27 **(decision)** One use is counted per invoice the discount appears on (`DiscountUsage`, unique per discount and invoice). The check and the count update happen in one transaction with the discount row locked, so concurrent runs cannot exceed the limit.
- FR-28 **(decision)** At most one product-level and one subscription-level discount per invoice. A discount never takes a line below zero. Dates, minimums and limits are re-checked at invoice time, not only when the rule is attached.

### 5.7 Payments
- FR-29 Record method, amount, date and note against an invoice.
- FR-30 **(decision)** Partial payments allowed. An invoice becomes Paid when payments cover the total. Overpayment is rejected with a clear message.
- FR-31 Staff can list paid, outstanding and overdue invoices. Overdue is derived (Confirmed, past due date, balance above zero), not a stored state.

### 5.8 Finance dashboard
- FR-32 One page: active subscriptions, revenue, payments, outstanding, overdue invoices, with filters and a summary view.
- FR-33 **(decision)** Revenue is shown as **Invoiced** and **Collected** separately. MRR is monthly-equivalent (yearly ÷ 12, weekly and daily converted), net of discount, excluding tax, and its definition is shown on screen.

### 5.9 Customer portal
- FR-34 A customer sees only their own subscriptions and invoices, with a print view. Where the plan allows, they can pause, close or renew from the portal.

## 6. Non-functional requirements
- NFR-1 Every page responds in under 2 seconds with thousands of subscriptions. Seed 5,000+ to prove it. Paginate on the server, index foreign keys, avoid N+1 queries (`selectinload`, `joinedload`), compute dashboard totals with SQL aggregates, debounce search (about 300 ms).
- NFR-2 Server-side validation on every input, with clear error messages.
- NFR-3 Responsive layout and consistent styling.
- NFR-4 Never commit secrets. No force pushes. Each person commits from their own account, with messages that explain why.
- NFR-5 Tests for state transitions, billing, discounts and portal access.

## 7. Acceptance checks
1. Signup rejects a duplicate email and an 8-character password, and accepts a valid 9-character one.
2. Staff cannot open admin screens or create staff. A customer cannot read another customer's invoice.
3. Choosing the Odoo brand adds 560 to the price.
4. A template creates a quote with correct lines and an expiry date.
5. A subscription walks through every allowed state, and illegal moves are rejected.
6. A Billing Run over 500 due subscriptions creates 500 invoices. A second run creates 0. A skipped day is caught up on the next run. Two runs started at the same time create no duplicates.
7. A discount with limit 5 and 20 simultaneous uses applies exactly 5 times, and appears on the next invoice with no manual step.
8. Payments move invoices to Paid, and the dashboard updates.
9. The dashboard and invoice list load under 2 seconds with 5,000 seeded subscriptions.

## 8. Out of scope
Multiple companies, payment gateway, proration on plan change, mobile app, GST invoice format, automatic reminder emails, microservices, AI features. If the core is finished, an optional "draft a quote from a sentence" feature is the only AI idea worth building, with human confirmation and the app fully working without it.

## 9. Confirm before submitting
- The organiser email or rules page confirms any stack is allowed and states the submission format and deadline.
- Which event this belongs to. This was inferred, not confirmed.

## 10. Not verified
How the event is judged beyond Odoo's published must-haves (dynamic data, clean responsive UI, input validation, navigation, Git use by more than one member). The billing guarantee follows patterns seen in Lago and OCA/contract and still needs to be tested on this codebase.
