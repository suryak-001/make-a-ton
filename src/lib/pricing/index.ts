// Owner: B. Pure functions, no DB access — A uses these for subscription/quotation line amounts
// and B uses them for invoices, so both sides always agree on the numbers.

export type TaxRule = { kind: "PERCENT" | "FIXED"; rate: number };
export type DiscountRule = { kind: "PERCENT" | "FIXED"; value: number };

export type LineInput = {
  unitPrice: number; // product sales price (or plan price)
  variantExtra?: number; // e.g. +560 for the Odoo brand
  quantity: number;
  taxes?: TaxRule[];
  discount?: DiscountRule | null;
};

export type LineResult = {
  unitPrice: number; // unitPrice + variantExtra
  subtotal: number; // before discount and tax
  discountAmount: number;
  taxAmount: number;
  total: number;
};

export const round2 = (n: number) => Math.round((n + Number.EPSILON) * 100) / 100;

export function computeLine({
  unitPrice,
  variantExtra = 0,
  quantity,
  taxes = [],
  discount,
}: LineInput): LineResult {
  const effectiveUnit = round2(unitPrice + variantExtra);
  const subtotal = round2(effectiveUnit * quantity);

  let discountAmount = 0;
  if (discount) {
    discountAmount =
      discount.kind === "PERCENT" ? round2((subtotal * discount.value) / 100) : round2(discount.value);
    discountAmount = Math.min(discountAmount, subtotal);
  }

  // Taxes apply to the discounted amount. FIXED taxes are per unit.
  const taxable = subtotal - discountAmount;
  const taxAmount = round2(
    taxes.reduce((sum, t) => sum + (t.kind === "PERCENT" ? (taxable * t.rate) / 100 : t.rate * quantity), 0),
  );

  return {
    unitPrice: effectiveUnit,
    subtotal,
    discountAmount,
    taxAmount,
    total: round2(taxable + taxAmount),
  };
}

export type Totals = { subtotal: number; discountTotal: number; taxTotal: number; total: number };

export function computeTotals(lines: LineResult[]): Totals {
  const sum = (pick: (l: LineResult) => number) => round2(lines.reduce((s, l) => s + pick(l), 0));
  return {
    subtotal: sum((l) => l.subtotal),
    discountTotal: sum((l) => l.discountAmount),
    taxTotal: sum((l) => l.taxAmount),
    total: sum((l) => l.total),
  };
}
