# Brightloop end-to-end test checklist

A script for walking the whole product in a browser, from the admin setting things up to a customer paying and
downloading an invoice. Work top to bottom: each part uses what the part before it created. Tick a box only when
you saw the result on screen. A failed step is written down with what you saw, not skipped.

## 0. Start the app

```bash
cd backend
createdb brightloop_dev                          # once
cp .env.example .env                             # set DATABASE_URL and SESSION_SECRET
uv run alembic upgrade head
uv run python -m app.seed                        # wipes the database, then loads the demo data below
uv run uvicorn app.main:app --port 8000          # use another port if 8000 is taken
cd ../frontend && npm install && npm run dev     # http://localhost:5173 (API_TARGET=http://localhost:<port> if not 8000)
```

Emails (password reset, invoices, reminders) are printed in the backend console unless `SMTP_HOST` is set.
Keep that console visible: several steps below say "check the console".

For the 5,000-subscription speed check, reseed with `uv run python -m app.seed --big` (part 15).

## 1. Logins

| Role | Email | Password | Lands on |
|---|---|---|---|
| Admin | admin@brightloop.test | Admin@12345 | /dashboard |
| Staff | staff@brightloop.test | Staff@12345 | /dashboard (work queue) |
| Customer | priya@acme.test | Customer@123 | /portal/home |

Passwords must be 9+ characters with an uppercase letter, a lowercase letter and a special character.

## 2. Demo data after the seed

- **Company on invoices:** Brightloop Software Pvt Ltd, Kochi (sample GSTIN, bank and UPI details).
- **Customers:** Acme Retail (portal login: Priya), Northwind Traders, Globex Corporation, each with an address.
- **Taxes:** GST 18%, GST 5%.
- **Products:** Brightloop CRM (variants Standard +0, Odoo +560), Analytics add-on (add-on), Priority support (add-on).
- **Plans:** Monthly (pausable, closable, renewable), Yearly contract (min quantity 5, closes by itself, not closable early),
  Weekly trial (closes by itself, not renewable).
- **Quotation template:** Enterprise yearly (Odoo), valid 30 days.
- **Discount:** Volume 10% (10+ seats), CRM only, limit 5 uses.
- **Subscriptions (5):** two active for Acme (one billed from 60 days ago, one starting in 5 days), one active yearly for
  Globex, a quotation and a draft for Northwind.
- **Invoices after seeding:** INV-2026-00001 (Acme, confirmed, overdue), INV-2026-00002 (Acme, paid in full by bank transfer),
  INV-2026-00003 (Globex, confirmed, 10% volume discount applied).

Demo payment gateway (online checkout, no real money):

| Method | Use | Result |
|---|---|---|
| Card | 4111 1111 1111 1111, any future expiry, any CVV, OTP 123456 | Approved |
| Card | 5555 5555 5555 4444 | Approved (Mastercard) |
| Card | 4000 0000 0000 0002 | Declined by bank |
| Card | 4000 0000 0000 9995 | Insufficient funds |
| Card | any card with a wrong OTP | Declined |
| UPI | success@demo / failure@demo | Approves / declines |
| Netbanking | HDFC, ICICI, SBI, Axis or Kotak, then choose success or failure | Approves / declines |

## 3. Sign-up, sign-in and password rules (signed out)

- [ ] /login shows the sign-in form; /signup and /forgot-password open from it.
- [ ] Sign up with a weak password (8 characters, no special character): the message names what is missing, on the field.
- [ ] Sign up with exactly 8 characters including upper, lower and special: refused (the minimum is 9).
- [ ] Sign up a new customer: `newcust@test.test` / `Newcust@123`. You land on the customer home with no subscriptions.
- [ ] Sign up again with `NEWCUST@test.test` (different case): refused, one account per email.
- [ ] Wrong password on sign-in gives a generic "invalid email or password".
- [ ] Forgot password for `priya@acme.test`: a reset link appears in the backend console. Open it, set `Reset@12345`, sign in
      with it, then change it back through the same flow to `Customer@123`.
- [ ] Forgot password for an unknown email: the same neutral message, no error, nothing in the console.
- [ ] Reusing the same reset link a second time is refused.
- [ ] Signed out, open /dashboard and /portal/home: you are sent to /login.

## 4. Admin: set up the business (sign in as admin)

- [ ] Dashboard (part 12) loads with numbers and no errors.
- [ ] **Users:** add a staff member `staff2@brightloop.test` / `Staff2@12345`. It appears in the list with the role Staff.
- [ ] Adding a user with a weak password or a duplicate email is refused with a clear message.
- [ ] **Taxes:** create "GST 12%" (percent, 12). Edit it. Create a fixed-amount tax. Deactivate one.
- [ ] **Products:** create "Brightloop Billing" (type Service, sales price 2000, cost price 500, notes). Add variants
      Brand: Odoo (+560) and Brand: Standard (+0). Attach GST 18% as a default tax. Mark one product as an add-on.
- [ ] **Plans:** create "Quarterly test" as Monthly, minimum quantity 2, available from today to 90 days out, with
      pausable, closable, renewable and auto-close set differently from the seeded plans. Edit it, then deactivate it.
- [ ] A plan with an end date before its start date is refused.
- [ ] **Discounts:** create a fixed ₹500 discount on a product, minimum quantity 3, start today, end in 30 days, limit 2.
      Create a percentage discount on a whole subscription. Edit and delete one.
- [ ] A discount with an end date before its start date, or a percentage over 100, is refused on the right field.
- [ ] **Quotation templates:** create "Starter pack" with a plan, two product lines and a validity of 14 days.
- [ ] Every page above is blocked for staff (part 5) and for the customer (part 9).

## 5. Staff: day-to-day work (sign in as staff)

- [ ] Dashboard is "Today's work": counts for drafts, overdue, renewals due, quotes expiring, plus the chase list. No MRR or
      revenue figures are shown.
- [ ] The sidebar has no Taxes, Discounts or Users. Opening /taxes, /discounts or /users directly shows the forbidden page.
- [ ] **Customers:** create "Initech Ltd" with an address, email and phone. Edit it. Search for it. Export the list to CSV.
- [ ] **Products and Plans:** staff can open them but have no create, edit or delete buttons.
- [ ] **Subscription from a template:** New subscription, pick the Enterprise yearly template, pick Initech, save.
      Lines, prices (Odoo +560), taxes and totals are filled in. It starts as Draft.
- [ ] Minimum quantity: set a line below the plan's minimum and save: refused with a message.
- [ ] **State machine:** move the subscription Draft → Quotation → Confirmed → Active. The status badge and the history
      timeline update each time, with who did it. An illegal jump is not offered.
- [ ] Opening the same subscription in two tabs and clicking Confirm twice does not confirm it twice.
- [ ] **Add-ons:** on an active subscription, switch Priority support on, then off. The lines and total change and the
      history records it.
- [ ] Pause and resume an active subscription on a pausable plan. A non-pausable plan offers no pause.
- [ ] Close a subscription on a closable plan; the yearly plan does not offer early close.
- [ ] Renew a subscription on a renewable plan; the weekly trial does not offer renew.
- [ ] **Run lifecycle job** (admin only, Subscriptions page; staff do not see the button): reports how many were closed and how many quotes expired.
- [ ] Subscriptions list: filter by status, customer and plan; page through; export to CSV with the same filters.

## 6. Billing day (staff or admin)

- [ ] **Billing run:** pick today as the bill-through date and run it. The result counts add up:
      due = created + already billed + skipped + failed.
- [ ] Run it again immediately: 0 new invoices.
- [ ] Set the bill-through date 2 months ahead: exactly the missing periods are created, nothing is duplicated.
- [ ] New invoices are Drafts with customer details, product lines, taxes and totals already filled in, and no invoice number yet.
- [ ] **Invoices list:** filter by status, customer, date range and "Overdue only"; export to CSV.
- [ ] Open a Draft: **Confirm** it. It now has an `INV-2026-` number and a Confirmed status.
- [ ] **Cancel** a Draft or Confirmed invoice (confirm the dialog). The status is Cancelled and the period is not billed again by
      the next billing run.
- [ ] As **admin**, **Re-bill** the cancelled invoice: a new Draft appears. Staff do not see the Re-bill button.
- [ ] Discount applies by itself: the Globex invoice (INV-2026-00003) shows the 10% volume discount. Create a 10+ seat
      subscription and bill it to see a new application. After the 5th use the discount stops appearing.
- [ ] **Send** a confirmed invoice: the console shows an email to the customer with an `INV-….pdf` attachment line.
- [ ] **Download PDF** (staff and admin): a PDF opens with the company letterhead, customer address, lines, discount, tax,
      totals, "How to pay" bank block and footer; a Paid invoice shows a PAID stamp and its payments; a Draft shows DRAFT.
- [ ] **Print** opens the print page.

## 7. Payments and overdue (staff or admin)

- [ ] **Record a payment** against INV-2026-00003: method, amount, date and note. Pay part of it first: the invoice stays Confirmed
      with a smaller outstanding amount. Pay the rest: it becomes Paid.
- [ ] Paying more than is owed is refused. Paying a Draft or Cancelled invoice is refused.
- [ ] Payments list: filter by method, customer and date; export to CSV.
- [ ] **Overdue:** INV-2026-00001 shows as overdue (red) in the Invoices list and on the dashboards.
- [ ] **Bank reconciliation:** open the page, use **Sample statement**. Sure and likely matches are ticked, the unknown refund is
      left for a person. Record the approved lines. Upload the same file again: every line says it was recorded before, and
      no payment is added twice.
- [ ] **Reminder (staff dashboard):** click **Send reminder** on the overdue invoice. The console shows the email and the button
      changes to "Sent for 1-30". Clicking again is not possible, and the API refuses a second reminder in the same stage.

## 8. Reports (staff or admin)

- [ ] Reports page: filter by date range, plan, customer and status. The summary, the revenue chart and the overdue list all react.
- [ ] Every money figure has two decimals. Hovering a figure shows its definition.
- [ ] Numbers agree between the dashboard, Reports and a customer's page.

## 9. Customer: the portal (sign in as priya@acme.test)

- [ ] Lands on **Home**: a red alert for the overdue invoice with the amount, "You owe", "Overdue" and "Next payment due" cards,
      the subscriptions with their buttons, and recent invoices.
- [ ] The sidebar shows only Home, My subscriptions and My invoices. Opening /dashboard, /invoices or /users shows the forbidden page.
- [ ] **My subscriptions:** only Acme's subscriptions, none from other customers, no drafts.
- [ ] Open the monthly subscription: **Pause** it (an undo toast appears; use Undo), then pause again and **Resume**.
- [ ] **Add-ons:** switch Priority support on, then off. The total changes and the history says who did it.
- [ ] **Close** a subscription on a closable plan (give a reason); the yearly contract offers no close.
- [ ] A plan that cannot be paused, closed or renewed shows no button and a note to get in touch.
- [ ] **My invoices:** only Acme's invoices. Open one and **Download PDF**: it opens in the company's name with the customer's
      own details. **Print** also works.
- [ ] Try another customer's invoice by editing the URL (for example /portal/invoices/3): "not found", never the invoice.
- [ ] **Pay online** on the overdue invoice:
  - [ ] Card 4000 0000 0000 0002: declined with a reason, the invoice stays open, you can retry.
  - [ ] Card 4111 1111 1111 1111 with a wrong OTP: declined.
  - [ ] Card 4111 1111 1111 1111 with OTP 123456: approved, the invoice becomes Paid, outstanding is ₹0.00, and the success
        screen appears.
  - [ ] UPI failure@demo declines; success@demo approves (try on another invoice).
  - [ ] Netbanking with a bank and "failure" declines; "success" approves.
  - [ ] Close the checkout tab after paying, then reload: the invoice still shows Paid (the server was told).
- [ ] After paying: the Home alert turns green ("all paid up") and the Paid invoice's PDF shows the PAID stamp and the payment.
- [ ] Sign out, then press Back: you cannot see the portal again.

## 10. Staff sees what the customer did (sign back in as staff or admin)

- [ ] The customer's payment is in Payments, the invoice is Paid, the overdue count and amount on the dashboards dropped.
- [ ] The subscription history shows the customer's pause, resume and add-on changes with the customer as the actor.
- [ ] **Customer page** (open Acme from Customers): their numbers, subscriptions, invoices, payments and one activity timeline.
- [ ] Download the paid invoice's PDF as staff: same content the customer saw.

## 11. Role and permission checks

- [ ] Staff cannot: add users, open Taxes, Discounts, Users, edit products or plans, or Re-bill (the page or button is missing and
      the API answers 403).
- [ ] Customers cannot open any staff page and cannot use staff API routes.
- [ ] Signed out: every page redirects to /login.

## 12. Dashboards

**Admin** (sign in as admin)
- [ ] Cards: Active subscriptions, Monthly revenue (net of discounts, before tax), Invoiced, Collected (shows "x% of invoiced").
- [ ] Revenue by month chart with 6 and 12 month toggles. Months with no data show as flat, not missing.
- [ ] Outstanding card; Overdue card. Clicking Overdue opens Invoices already filtered to overdue.
- [ ] Overdue invoices table; clicking a row opens that invoice.
- [ ] "How these numbers are calculated" explains every figure.
- [ ] **Aging of unpaid invoices:** Current, 1–30, 31–60, 61–90 and 90+ buckets with amount and count.
- [ ] **Proof panel:** row counts, "0 subscriptions billed twice for the same period", and the milliseconds the checks took.
- [ ] **Next-step banner:** on a freshly emptied database (no products yet) it says "Add a product to sell". After you add a product,
      plan, subscription, run billing and record a payment, it moves along each time and disappears when all five are done.

**Staff** — see part 5 and 7. **Customer** — see part 9.

## 13. Invoice PDF and email

- [ ] Staff and admin: Download PDF on a Draft, a Confirmed, a Paid and a Cancelled invoice. Each stamp is correct.
- [ ] Customer: Download PDF only works for their own, confirmed or paid invoices.
- [ ] Send an invoice: the console shows the company-named subject, the amount, the due date and the PDF attachment.
- [ ] The PDF opens in a normal PDF viewer and prints on one A4 page.

## 14. Edge cases

- [ ] Empty states read well (a new customer with no subscriptions, a database with no invoices).
- [ ] Forms keep what you typed when the server refuses them, and the message is on the right field.
- [ ] Narrow phone-width browser: tables turn into cards, no sideways scrolling, buttons stay reachable.
- [ ] Money always shows ₹ with two decimals in the app, and `INR` in the PDF.
- [ ] Dates are shown the same way everywhere (for example 21 Oct 2026).
- [ ] Browser console has no red errors on any page visited.

## 15. Speed with thousands of subscriptions

- [ ] Reseed with `uv run python -m app.seed --big` (5,000 subscriptions, about 11,500 invoices, 9,000 payments).
- [ ] Admin dashboard, Reports, Invoices, Payments, Subscriptions and Customers each load in under 2 seconds.
- [ ] The proof panel's "ms" figure is small, and filters respond without lag.
- [ ] Run the billing run on the big data set and confirm the counts still add up.

## 16. Repo and code checks

```bash
cd backend && uv run ruff check . && uv run pytest        # all tests pass
cd frontend && npm run lint && npm run build              # no errors
git log --oneline | head -20                              # several authors, descriptive messages
```

- [ ] README run steps work from a clean clone.
- [ ] No secrets in the repo (`git grep -i "api_key\|secret"` shows only variable names and the example file).

## Result log

For each failed box, write: the step number, what you did, what you saw, and what you expected.
