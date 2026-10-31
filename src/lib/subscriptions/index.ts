// Owner: A (step A7). Contract: an ACTIVE subscription always has nextInvoiceDate, paymentTermDays
// and at least one line — B's billing run relies on that.
import "server-only";
import type { Plan, Subscription } from "@/generated/prisma/client";
import type { SubscriptionStatus } from "@/generated/prisma/enums";

export const SUBSCRIPTION_TRANSITIONS: Record<SubscriptionStatus, SubscriptionStatus[]> = {
  DRAFT: ["QUOTATION", "CLOSED"],
  QUOTATION: ["CONFIRMED", "DRAFT", "CLOSED"],
  CONFIRMED: ["ACTIVE", "CLOSED"],
  ACTIVE: ["PAUSED", "CLOSED"], // PAUSED only if plan.pausable, early CLOSED only if plan.closable
  PAUSED: ["ACTIVE", "CLOSED"],
  CLOSED: [],
};

export function canTransition(
  sub: Pick<Subscription, "status">,
  to: SubscriptionStatus,
  plan: Pick<Plan, "pausable" | "closable">,
): boolean {
  if (!SUBSCRIPTION_TRANSITIONS[sub.status].includes(to)) return false;
  if (to === "PAUSED" && !plan.pausable) return false;
  if (to === "CLOSED" && sub.status === "ACTIVE" && !plan.closable) return false;
  return true;
}

/**
 * Moves a subscription to a new status, enforcing canTransition.
 * On → ACTIVE: set nextInvoiceDate = startDate (if not already set).
 */
export async function transitionSubscription(id: string, to: SubscriptionStatus): Promise<Subscription> {
  void id;
  void to;
  throw new Error("TODO(A7): transitionSubscription");
}

/** Daily job (A8): close expired subs whose plan.autoClose is on, expire stale quotations. Idempotent. */
export async function runLifecycleJob(asOf: Date): Promise<{ closed: number; expiredQuotations: number }> {
  void asOf;
  throw new Error("TODO(A8): runLifecycleJob");
}
