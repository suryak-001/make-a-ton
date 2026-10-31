import type { TaxRule } from './types'
import { money } from './format'

/** "18%" for a percentage tax, "₹3.00" for a fixed per-unit one. */
export const taxRateLabel = (tax: Pick<TaxRule, 'kind' | 'rate'>) => (tax.kind === 'PERCENT' ? `${Number(tax.rate)}%` : money(tax.rate))
