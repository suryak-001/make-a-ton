export const CURRENCY = "INR";

type Numeric = number | string | { toString(): string }; // accepts Prisma.Decimal

export function money(value: Numeric | null | undefined) {
  return new Intl.NumberFormat("en-IN", { style: "currency", currency: CURRENCY }).format(Number(value ?? 0));
}

export function date(value: Date | string | null | undefined) {
  if (!value) return "—";
  return new Intl.DateTimeFormat("en-IN", { dateStyle: "medium", timeZone: "UTC" }).format(new Date(value));
}
