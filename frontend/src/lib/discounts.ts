import type { Discount } from './types'
import { money } from './format'

export type DiscountDraft = {
  name: string
  kind: Discount['kind']
  value: string
  scope: Discount['scope']
  start_date: string
  end_date: string
  min_purchase: string
  min_quantity: string
  usage_limit: string
  active: boolean
  product_ids: number[]
  subscription_ids: number[]
}

export const discountToDraft = (d: Discount): DiscountDraft => ({
  name: d.name,
  kind: d.kind,
  value: d.value,
  scope: d.scope,
  start_date: d.start_date,
  end_date: d.end_date ?? '',
  min_purchase: d.min_purchase ?? '',
  min_quantity: d.min_quantity?.toString() ?? '',
  usage_limit: d.usage_limit?.toString() ?? '',
  active: d.active,
  product_ids: d.product_ids,
  subscription_ids: d.subscription_ids,
})

const numberOrNull = (text: string) => (text ? Number(text) : null)

/** What the API expects: empty boxes become null, and only the chosen scope's targets are sent. */
export const discountToBody = (d: DiscountDraft) => ({
  ...d,
  value: d.value || '0',
  min_purchase: d.min_purchase || null,
  min_quantity: numberOrNull(d.min_quantity),
  end_date: d.end_date || null,
  usage_limit: numberOrNull(d.usage_limit),
  product_ids: d.scope === 'PRODUCT' ? d.product_ids : [],
  subscription_ids: d.scope === 'SUBSCRIPTION' ? d.subscription_ids : [],
})

export const discountValueLabel = (d: Pick<Discount, 'kind' | 'value'>) => (d.kind === 'PERCENT' ? `${Number(d.value)}%` : money(d.value))
