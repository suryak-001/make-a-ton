// Owner: B (step B3).
import "server-only";
import type { Discount } from "@/generated/prisma/client";

/**
 * Discounts that apply to a subscription on a given date: active, within start/end dates,
 * usedCount < usageLimit, min purchase / min quantity met, and scoped to the subscription
 * itself (SUBSCRIPTION) or to products on its lines (PRODUCT).
 */
export async function findApplicableDiscounts(subscriptionId: string, asOf: Date): Promise<Discount[]> {
  void subscriptionId;
  void asOf;
  throw new Error("TODO(B3): findApplicableDiscounts");
}
