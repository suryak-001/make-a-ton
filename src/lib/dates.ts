import type { BillingPeriod } from "@/generated/prisma/enums";

/** Next period start. Month/year math clamps to the last day (Jan 31 + 1 month = Feb 28/29). */
export function addPeriod(date: Date, period: BillingPeriod, count = 1): Date {
  const d = new Date(date);
  switch (period) {
    case "DAILY":
      d.setUTCDate(d.getUTCDate() + count);
      return d;
    case "WEEKLY":
      d.setUTCDate(d.getUTCDate() + 7 * count);
      return d;
    case "MONTHLY":
    case "YEARLY": {
      const months = period === "MONTHLY" ? count : 12 * count;
      const day = d.getUTCDate();
      d.setUTCDate(1);
      d.setUTCMonth(d.getUTCMonth() + months);
      const lastDay = new Date(Date.UTC(d.getUTCFullYear(), d.getUTCMonth() + 1, 0)).getUTCDate();
      d.setUTCDate(Math.min(day, lastDay));
      return d;
    }
  }
}

export function addDays(date: Date, days: number): Date {
  const d = new Date(date);
  d.setUTCDate(d.getUTCDate() + days);
  return d;
}

export function startOfDayUTC(date = new Date()): Date {
  return new Date(Date.UTC(date.getUTCFullYear(), date.getUTCMonth(), date.getUTCDate()));
}
