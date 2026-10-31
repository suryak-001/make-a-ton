// Owner: B (steps B4, B5). Contract: never two invoices for the same (subscriptionId, periodStart) —
// enforced by the DB unique constraint; catch P2002 and return the existing invoice.
import "server-only";
import type { Invoice } from "@/generated/prisma/client";

/**
 * Creates the invoice for one billing period of a subscription, in a single transaction:
 * snapshot lines → apply taxes + applicable discounts (lib/pricing) → record DiscountUsage,
 * increment Discount.usedCount → number via nextNumber(`INV-${year}`, ...) → dueDate = invoiceDate + paymentTermDays.
 * Idempotent: calling it twice for the same period returns the existing invoice.
 */
export async function generateInvoiceForPeriod(subscriptionId: string, periodStart: Date): Promise<Invoice> {
  void subscriptionId;
  void periodStart;
  throw new Error("TODO(B4): generateInvoiceForPeriod");
}

export type BillingRunResult = { created: number; skipped: number; errors: { subscriptionId: string; message: string }[] };

/**
 * For every ACTIVE subscription with nextInvoiceDate <= asOf: generate one invoice per due period
 * (catch-up, so nothing is skipped) and advance nextInvoiceDate with addPeriod(). Safe to run repeatedly.
 */
export async function runBilling(asOf: Date): Promise<BillingRunResult> {
  void asOf;
  throw new Error("TODO(B5): runBilling");
}
