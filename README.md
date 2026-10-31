# Brightloop: Subscription Management System

Plans, subscriptions, recurring billing, payments and reporting in one app. See **[PLAN.md](PLAN.md)** for the requirements, the two-person split and the timeline.

**Stack:** Next.js 16 (App Router) · TypeScript · Prisma 7 + PostgreSQL · Tailwind 4 + shadcn/ui (Base UI) · iron-session · Zod · Vitest

## Setup

Prerequisites: Node 22+ and a local PostgreSQL.

```bash
cp .env.example .env          # set DATABASE_URL and SESSION_SECRET (32+ chars)
createdb brightloop_dev
npm install                   # also runs `prisma generate`
npm run db:migrate            # apply migrations
npm run db:seed               # demo data (wipes the DB first)
npm run dev                   # http://localhost:3000
```

### Demo logins (from `prisma/seed.ts`)

| Role | Email | Password |
|------|-------|----------|
| Admin | admin@brightloop.test | Admin@12345 |
| Staff | staff@brightloop.test | Staff@12345 |
| Customer (portal) | priya@acme.test | Customer@123 |

Emails (password reset, invoices) are printed to the dev-server console unless `SMTP_HOST` is set.

## Scripts

| Script | What it does |
|--------|--------------|
| `npm run dev` | Dev server |
| `npm run build` | Production build |
| `npm test` | Vitest unit tests (`src/**/*.test.ts`) |
| `npm run typecheck` | Generate route types and run `tsc` |
| `npm run lint` | ESLint |
| `npm run db:migrate -- --name <change>` | Create and apply a migration after editing `schema.prisma` |
| `npm run db:seed` / `db:reset` | Re-seed / drop, re-migrate and re-seed |
| `npm run db:studio` | Prisma Studio |

## Where things live

```
prisma/schema.prisma      full data model (SHARED: ping your teammate before editing)
prisma/seed.ts            demo data (section A / section B)
src/proxy.ts              optimistic route guard (Next 16's "middleware")
src/lib/auth/             sessions, requireRole(), password policy          [A]
src/lib/subscriptions/    state machine + lifecycle job (stubs)             [A]
src/lib/pricing/          line/tax/discount math: implemented + tested      [B]
src/lib/billing/          invoice generation + billing run (stubs)          [B]
src/lib/discounts/        applicable-discount lookup (stub)                 [B]
src/lib/sequence.ts       atomic SUB-/INV- numbering
src/lib/nav.ts            sidebar menu, role visibility, owner + checklist per page
src/app/(auth)/           login (works), signup/forgot/reset (placeholders)
src/app/(app)/            back office for admin + staff
src/app/portal/           customer portal
```

Every page not built yet shows its PLAN.md checklist and owner. Replace the placeholder with the real page.

## Conventions

- **Authorize close to the data.** Call `requireRole(...)` at the top of every page, server action and route handler. Layouts and `proxy.ts` are not an auth boundary.
- **Customers see only their own records.** Scope portal queries with `session.customerId`.
- **Money:** `Decimal(12,2)` in the DB. All arithmetic goes through `src/lib/pricing`, and display goes through `money()` in `src/lib/format.ts`.
- **Numbers:** use `nextNumber()`, never `count() + 1`.
- **Prisma client** is generated into `src/generated/prisma` (gitignored). Import from `@/generated/prisma/client` and use `db` from `@/lib/db`.
- **shadcn/ui** here uses Base UI, so components take a `render` prop instead of `asChild`. Add components with `npx shadcn@latest add <name>`.
- Branch per feature, small PRs, rebase on `main` often. One migration per PR.
