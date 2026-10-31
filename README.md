# Brightloop: Subscription Management System

Plans, subscriptions, recurring billing, payments and reporting in one app. See **[PLAN.md](PLAN.md)** for the build plan and split (Person A backend, Person B frontend), **[docs/PRD.md](docs/PRD.md)** for the requirements, and **[docs/API_CONTRACT.md](docs/API_CONTRACT.md)** for the API contract.

**Stack:** FastAPI + SQLAlchemy 2 + Alembic + PostgreSQL (Python 3.13) · React 19 + TypeScript + Vite + Tailwind 4 + React Router + TanStack Query

```
backend/    FastAPI API, models, migrations, seed, pytest
frontend/   React app (talks to the API through Vite's /api proxy)
```

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

### Demo logins (from `backend/app/seed.py`)

| Role | Email | Password |
|------|-------|----------|
| Admin | admin@brightloop.test | Admin@12345 |
| Staff | staff@brightloop.test | Staff@12345 |
| Customer (portal) | priya@acme.test | Customer@123 |

Emails (password reset, invoices) are printed to the backend console unless `SMTP_HOST` is set.

## Everyday commands

| Where | Command | What it does |
|-------|---------|--------------|
| backend | `uv run pytest` | Tests (needs a `brightloop_test` database: `createdb brightloop_test`) |
| backend | `uv run ruff check . && uv run ruff format .` | Lint and format |
| backend | `uv run alembic revision --autogenerate -m "what changed"` | New migration after editing `app/models` |
| backend | `uv run alembic upgrade head` | Apply migrations |
| backend | `uv run python -m app.seed` | Reset demo data |
| frontend | `npm run build` | Type check and production build |
| frontend | `npm run lint` | oxlint |

## Where things live

```
backend/app/models/         full data model (SHARED: ping your teammate before editing)
backend/app/core/           password policy, session cookie, get_current_user, require_roles   [A]
backend/app/routers/        one file per module: auth works, the rest are empty stubs
backend/app/services/       pricing (done, tested) · billing/discounts (stubs, B) · subscriptions (stubs, A)
backend/app/services/sequence.py   atomic SUB-/INV- numbering
backend/app/seed.py         demo data (section A / section B)
frontend/src/nav.ts         sidebar menu, role visibility, owner + checklist per page
frontend/src/routes.tsx     routes; auto-registers pages from src/pages/<route>/index.tsx
frontend/src/auth/          session state and the role route guard
frontend/src/lib/api.ts     fetch wrapper (cookies, errors)
```

Every page not built yet shows its PLAN.md checklist and owner. To build one, create `frontend/src/pages/<route>/index.tsx` with a default export (e.g. `src/pages/subscriptions/index.tsx`) and it replaces the placeholder automatically. Then implement the matching router in `backend/app/routers/`.

## Conventions

- **Authorize on the server, on every route.** Add `Depends(require_roles(...))` (or the `AdminUser` / `StaffUser` / `CustomerUser` aliases from `app.core.deps`) to every endpoint that touches data. The frontend route guard only decides what to render.
- **Customers see only their own records.** Scope portal queries by `user.customer.id`.
- **Money is `Decimal`** in Python and `Numeric(12,2)` in the DB; it travels as a string in JSON. All arithmetic goes through `app/services/pricing.py`. The frontend never recomputes totals: it calls `POST /api/pricing/preview` and formats with `money()` from `src/lib/format.ts`.
- **Numbers:** use `next_number()`, never `count() + 1`.
- **Email format is validated on signup, not login.** `EmailStr` rejects reserved domains like `.test`, which the demo users use.
- Branch per feature, small PRs, rebase on `main` often. One migration per PR.
