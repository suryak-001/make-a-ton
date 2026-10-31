import { describe, expect, it } from "vitest";
import { computeLine, computeTotals } from ".";

describe("computeLine", () => {
  it("adds the variant extra price (Odoo brand +560)", () => {
    const r = computeLine({ unitPrice: 1000, variantExtra: 560, quantity: 2 });
    expect(r.unitPrice).toBe(1560);
    expect(r.subtotal).toBe(3120);
    expect(r.total).toBe(3120);
  });

  it("applies a percent discount before percent tax", () => {
    const r = computeLine({
      unitPrice: 100,
      quantity: 10,
      discount: { kind: "PERCENT", value: 10 },
      taxes: [{ kind: "PERCENT", rate: 18 }],
    });
    expect(r.discountAmount).toBe(100);
    expect(r.taxAmount).toBe(162);
    expect(r.total).toBe(1062);
  });

  it("caps a fixed discount at the subtotal", () => {
    const r = computeLine({ unitPrice: 50, quantity: 1, discount: { kind: "FIXED", value: 80 } });
    expect(r.discountAmount).toBe(50);
    expect(r.total).toBe(0);
  });

  it("stacks multiple taxes, fixed taxes per unit", () => {
    const r = computeLine({
      unitPrice: 200,
      quantity: 3,
      taxes: [
        { kind: "PERCENT", rate: 9 },
        { kind: "FIXED", rate: 5 },
      ],
    });
    expect(r.taxAmount).toBe(69); // 54 + 15
    expect(r.total).toBe(669);
  });
});

describe("computeTotals", () => {
  it("sums lines", () => {
    const a = computeLine({ unitPrice: 10, quantity: 1, taxes: [{ kind: "PERCENT", rate: 10 }] });
    const b = computeLine({ unitPrice: 20, quantity: 2, discount: { kind: "FIXED", value: 5 } });
    expect(computeTotals([a, b])).toEqual({ subtotal: 50, discountTotal: 5, taxTotal: 1, total: 46 });
  });
});
