# Brightloop: Subscription Management System

Plans, subscriptions, recurring billing, payments and reporting in one app. See **[PLAN.md](PLAN.md)** for the build plan and split (sell side and money side), **[docs/PRD.md](docs/PRD.md)** for the requirements, and **[docs/API_CONTRACT.md](docs/API_CONTRACT.md)** for the API contract.

**Stack:** FastAPI + SQLAlchemy 2 + Alembic + PostgreSQL (Python 3.13) · React 19 + TypeScript + Vite + Tailwind 4 + React Router + TanStack Query

```
backend/    FastAPI API, models, migrations, seed, pytest
frontend/   React app (talks to the API through Vite's /api proxy)
```

## For judges: see it working in five minutes

1. Run the setup below (about five commands), then open the app and sign in with the demo logins.
2. Follow this path. Everything needed is already in the demo data.

| Step | Sign in as | Do this | What you should see |
|------|-----------|---------|---------------------|
| 1 | nobody | Sign up with a weak password, then a valid one; try the same email in capitals; use **Forgot password** | Rules named on the field, one account per email, reset link printed in the backend console |
| 2 | Admin | **Users** → Add staff member → copy the invite | Staff are added only by the admin; the staff member must pick their own password at first sign-in |
| 3 | Admin | **Products**, **Plans**, **Taxes**, **Discounts** | Variants (Odoo +560), plans that close, pause or renew, tax and discount rules |
| 4 | Staff | **Quotation templates** → use the template for a customer → Draft → Quotation → Confirmed → Active | Lines, prices and taxes filled in by the server; history shows who did what |
| 5 | Staff | **Billing run** (set a date two months ahead), run it twice | Invoices created from subscriptions; the second run creates none; counts add up |
| 6 | Staff | Open a Draft invoice → Confirm, Send to customer, Download PDF, then Record payment (try a part-payment first) | Invoice number at confirm, the volume discount applied by itself, PDF with the PAID stamp once settled |
| 7 | Customer (Priya) | **Home** → Pay the open invoice with card `4111 1111 1111 1111`, OTP `123456`; try Pause or Cancel subscription on a monthly plan | Invoice turns Paid; pause, renew and cancel appear only where the plan allows |
| 8 | Admin | **Dashboard**, **Reports** | Active subscriptions, revenue, collected, overdue, aging, filters; every page answers in under two seconds even with `--big` data |
| 9 | Staff | **Bank reconciliation** → Try with a sample statement → Record payments (do this last: it settles the seeded overdue invoice) | Credits matched to open invoices with the reason shown; run it again and nothing is paid twice |

**Where each part of the brief lives:** sign-up, roles and password rules (`/signup`, `/users`) · products and variants (`/products`) · plans (`/plans`) · quotation templates and the subscription life cycle (`/quotation-templates`, `/subscriptions`) · billing day and invoices (`/billing-run`, `/invoices`) · discounts (`/discounts`) · payments (`/payments`, `/reconciliation`) · finance view (`/dashboard`, `/reports`) · customer portal (`/portal/*`). The full click-through script is in [docs/TEST_CHECKLIST.md](docs/TEST_CHECKLIST.md).

**Honest limits:** emails (reset, invites, invoices) are printed in the backend console unless SMTP is configured; the payment gateway is a built-in test-mode simulator; the billing run is one request (35,000 invoices take about two minutes), fine for hundreds due at once.

## Setup

Prerequisites: [uv](https://docs.astral.sh/uv/) (installs Python 3.13 for you), Node 22+, and a local PostgreSQL.

```bash
# Backend
cd backend
cp .env.example .env                      # set DATABASE_URL (your Postgres user) and SESSION_SECRET
createdb brightloop_dev
uv sync                                   # creates .venv with Python 3.13 and installs dependencies
uv run alembic upgrade head               # create the tables
uv run python -m app.seed                 # demo data (wipes the DB first)
uv run uvicorn app.main:app --reload      # http://localhost:8000  (API docs: /docs)
```

```bash
# Frontend (second terminal)
cd frontend
npm install
npm run dev                               # http://localhost:5173
```

Open http://localhost:5173.

**Daily jobs.** The server bills everything due and then runs the lifecycle job (auto-close, quote expiry) every day at 02:00 server time. For a demo, use **Billing Run** and the lifecycle button in the app instead, so the numbers appear on screen. To also catch up shortly after start-up set `SCHEDULER_RUN_ON_START=true`; to turn the scheduler off set `SCHEDULER_ENABLED=false`.

### Demo logins (from `backend/app/seed.py`)

| Role | Email | Password |
|------|-------|----------|
| Admin | admin@brightloop.test | Admin@12345 |
| Staff | staff@brightloop.test | Staff@12345 |
| Customer (portal) | priya@acme.test | Customer@123 |

Emails (password reset, invoices) are printed to the backend console unless `SMTP_HOST` is set.

### Paying online (demo gateway)

Customers pay a confirmed invoice from **My invoices → Pay**. The checkout talks to a built-in demo gateway (`backend/app/services/gateway.py`), test mode only: no real money moves, and only these details are accepted.

| Method | Approves | Declines |
|--------|----------|----------|
| Card (any future expiry, any CVV, OTP `123456`) | `4111 1111 1111 1111`, `5555 5555 5555 4444` | `4000 0000 0000 0002` (bank declines), `4000 0000 0000 9995` (insufficient funds) |
| UPI | `success@demo` | `failure@demo` |
| Netbanking | choose *Simulate success* on the bank page | choose *Simulate failure* |

The flow matches a real Indian gateway (server-side order, signed result checked by the server, a server-to-server notification as a webhook would send), so swapping in Razorpay later means replacing the gateway service, not the screens.

## Everyday commands

| Where | Command | What it does |
|-------|---------|--------------|
| backend | `uv run pytest` | Tests (needs a `brightloop_test` database: `createdb brightloop_test`) |
| backend | `uv run ruff check . && uv run ruff format .` | Lint and format |
| backend | `uv run alembic revision --autogenerate -m "what changed"` | New migration after editing `app/models` |
| backend | `uv run alembic upgrade head` | Apply migrations |
| backend | `uv run python -m app.seed` | Reset demo data, invoices and payments |
| backend | `uv run python -m app.seed --big` | Seed 5,000 subscriptions for performance checks |
| frontend | `npm run build` | Type check and production build |
| frontend | `npm run lint` | oxlint |

## Where things live

```
backend/app/models/         full data model (SHARED: ping your teammate before editing)
backend/app/core/           password policy, session cookie, current user and role guards
backend/app/routers/        complete APIs for identity, selling, billing, reports and both portals
backend/app/services/       pricing, subscriptions, billing, discounts, invoices and view builders
backend/app/services/sequence.py   atomic SUB-/INV- numbering
backend/app/seed.py         demo data (section A / section B)
frontend/src/nav.ts         sidebar menu, role visibility, owner + checklist per page
frontend/src/routes.tsx     routes; auto-registers pages from src/pages/<route>/index.tsx
frontend/src/auth/          session state and the role route guard
frontend/src/lib/api.ts     fetch wrapper (cookies, errors)
```

Pages are auto-registered from `frontend/src/pages/<route>/index.tsx`; nested detail and form routes live beside each page.

## Conventions

- **Authorize on the server, on every route.** Add `Depends(require_roles(...))` (or the `AdminUser` / `StaffUser` / `CustomerUser` aliases from `app.core.deps`) to every endpoint that touches data. The frontend route guard only decides what to render.
- **Customers see only their own records.** Scope portal queries by `user.customer.id`.
- **Money is `Decimal`** in Python and `Numeric(12,2)` in the DB; it travels as a string in JSON. All arithmetic goes through `app/services/pricing.py`. The frontend never recomputes totals: it calls `POST /api/pricing/preview` and formats with `money()` from `src/lib/format.ts`.
- **Numbers:** use `next_number()`, never `count() + 1`.
- **Email format is validated on signup, not login.** `EmailStr` rejects reserved domains like `.test`, which the demo users use.
- Branch per feature, small PRs, rebase on `main` often. One migration per PR.
