// Dev seed — wipes and recreates demo data. Run with `npm run db:seed` (or `npm run db:reset`).
// SHARED FILE: Person A edits section A, Person B edits section B.
import "dotenv/config";
import { PrismaPg } from "@prisma/adapter-pg";
import bcrypt from "bcryptjs";
import { PrismaClient } from "../src/generated/prisma/client";
import { computeLine } from "../src/lib/pricing";

const db = new PrismaClient({ adapter: new PrismaPg({ connectionString: process.env.DATABASE_URL }) });

const DAY = 24 * 60 * 60 * 1000;
const today = new Date(new Date().toISOString().slice(0, 10)); // UTC midnight
const daysFromNow = (n: number) => new Date(today.getTime() + n * DAY);

async function nextNumber(name: string, prefix: string) {
  const rows = await db.$queryRaw<{ next: number }[]>`
    INSERT INTO "Sequence" ("name", "next") VALUES (${name}, 2)
    ON CONFLICT ("name") DO UPDATE SET "next" = "Sequence"."next" + 1
    RETURNING "next"`;
  return `${prefix}${String(rows[0].next - 1).padStart(5, "0")}`;
}

async function wipe() {
  const tables = await db.$queryRaw<{ tablename: string }[]>`
    SELECT tablename FROM pg_tables WHERE schemaname = 'public' AND tablename <> '_prisma_migrations'`;
  const list = tables.map((t) => `"public"."${t.tablename}"`).join(", ");
  if (list) await db.$executeRawUnsafe(`TRUNCATE TABLE ${list} RESTART IDENTITY CASCADE`);
}

async function main() {
  await wipe();

  // ─────────────────────── Shared: users (passwords meet the policy) ───────────────────────
  const hash = (p: string) => bcrypt.hash(p, 10);
  const admin = await db.user.create({
    data: { email: "admin@brightloop.test", name: "Ada Admin", role: "ADMIN", passwordHash: await hash("Admin@12345") },
  });
  await db.user.create({
    data: { email: "staff@brightloop.test", name: "Sam Staff", role: "STAFF", passwordHash: await hash("Staff@12345") },
  });
  const customerUser = await db.user.create({
    data: { email: "priya@acme.test", name: "Priya (Acme)", role: "CUSTOMER", passwordHash: await hash("Customer@123") },
  });

  // ─────────────────────── Section B: taxes ───────────────────────
  const gst18 = await db.tax.create({ data: { name: "GST 18%", kind: "PERCENT", rate: 18 } });
  await db.tax.create({ data: { name: "GST 5%", kind: "PERCENT", rate: 5 } });

  // ─────────────────────── Section A: customers, catalog, plans, templates ───────────────────────
  const acme = await db.customer.create({
    data: { name: "Acme Retail", email: "priya@acme.test", phone: "+91 98765 43210", userId: customerUser.id },
  });
  const northwind = await db.customer.create({ data: { name: "Northwind Traders", email: "billing@northwind.test" } });
  const globex = await db.customer.create({ data: { name: "Globex Corporation", email: "ap@globex.test" } });

  const crm = await db.product.create({
    data: {
      name: "Brightloop CRM",
      type: "SERVICE",
      salesPrice: 1200,
      costPrice: 300,
      notes: "Per-seat CRM licence",
      defaultTaxes: { connect: { id: gst18.id } },
      variants: {
        create: [
          { attribute: "Brand", value: "Standard", extraPrice: 0 },
          { attribute: "Brand", value: "Odoo", extraPrice: 560 },
        ],
      },
    },
    include: { variants: true },
  });
  const analytics = await db.product.create({
    data: { name: "Analytics add-on", type: "SERVICE", salesPrice: 400, costPrice: 80, defaultTaxes: { connect: { id: gst18.id } } },
  });
  const support = await db.product.create({
    data: { name: "Priority support", type: "SERVICE", salesPrice: 800, costPrice: 200, defaultTaxes: { connect: { id: gst18.id } } },
  });
  const odoo = crm.variants.find((v) => v.value === "Odoo")!;

  const monthly = await db.plan.create({
    data: { name: "Monthly", price: 0, billingPeriod: "MONTHLY", minQuantity: 1, closable: true, pausable: true, renewable: true },
  });
  const yearly = await db.plan.create({
    data: { name: "Yearly contract", price: 0, billingPeriod: "YEARLY", minQuantity: 5, autoClose: true, closable: false, renewable: true },
  });
  await db.plan.create({
    data: { name: "Weekly trial", price: 0, billingPeriod: "WEEKLY", autoClose: true, renewable: false, availableTo: daysFromNow(90) },
  });

  await db.quotationTemplate.create({
    data: {
      name: "Enterprise yearly (Odoo)",
      planId: yearly.id,
      validityDays: 30,
      lines: {
        create: [
          { productId: crm.id, variantId: odoo.id, quantity: 10 },
          { productId: support.id, quantity: 1 },
        ],
      },
    },
  });

  type SeedLine = { productId: string; variantId?: string; price: number; extra?: number; qty: number };
  async function subscription(opts: {
    customerId: string;
    planId: string;
    status: "DRAFT" | "QUOTATION" | "CONFIRMED" | "ACTIVE";
    startDate: Date;
    expiryDate?: Date;
    lines: SeedLine[];
  }) {
    return db.subscription.create({
      data: {
        number: await nextNumber("SUB", "SUB-"),
        customerId: opts.customerId,
        planId: opts.planId,
        status: opts.status,
        startDate: opts.startDate,
        expiryDate: opts.expiryDate,
        paymentTermDays: 15,
        quotationValidUntil: opts.status === "QUOTATION" ? daysFromNow(30) : undefined,
        nextInvoiceDate: opts.status === "ACTIVE" ? opts.startDate : undefined,
        createdById: admin.id,
        lines: {
          create: opts.lines.map((l) => {
            const r = computeLine({ unitPrice: l.price, variantExtra: l.extra, quantity: l.qty, taxes: [{ kind: "PERCENT", rate: 18 }] });
            return {
              productId: l.productId,
              variantId: l.variantId,
              quantity: l.qty,
              unitPrice: r.unitPrice,
              amount: r.total,
              taxes: { connect: { id: gst18.id } },
            };
          }),
        },
      },
    });
  }

  await subscription({
    customerId: acme.id,
    planId: monthly.id,
    status: "ACTIVE",
    startDate: daysFromNow(-60), // two periods due → exercises billing catch-up
    lines: [
      { productId: crm.id, price: 1200, qty: 3 },
      { productId: analytics.id, price: 400, qty: 1 },
    ],
  });
  await subscription({
    customerId: globex.id,
    planId: yearly.id,
    status: "ACTIVE",
    startDate: daysFromNow(-10),
    expiryDate: daysFromNow(355),
    lines: [
      { productId: crm.id, variantId: odoo.id, price: 1200, extra: 560, qty: 12 },
      { productId: support.id, price: 800, qty: 1 },
    ],
  });
  await subscription({
    customerId: northwind.id,
    planId: monthly.id,
    status: "QUOTATION",
    startDate: daysFromNow(7),
    lines: [{ productId: crm.id, price: 1200, qty: 5 }],
  });
  await subscription({
    customerId: northwind.id,
    planId: monthly.id,
    status: "DRAFT",
    startDate: daysFromNow(14),
    lines: [{ productId: analytics.id, price: 400, qty: 2 }],
  });

  // ─────────────────────── Section B: discounts (invoices/payments come from the billing run) ───────────────────────
  await db.discount.create({
    data: {
      name: "Volume 10% (10+ seats)",
      kind: "PERCENT",
      value: 10,
      minQuantity: 10,
      startDate: daysFromNow(-30),
      endDate: daysFromNow(90),
      usageLimit: 5,
      scope: "PRODUCT",
      products: { connect: { id: crm.id } },
    },
  });

  console.log("Seeded. Logins: admin@brightloop.test / Admin@12345, staff@brightloop.test / Staff@12345, priya@acme.test / Customer@123");
}

main()
  .catch((e) => {
    console.error(e);
    process.exit(1);
  })
  .finally(() => db.$disconnect());
