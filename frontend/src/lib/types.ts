// API shapes for Person A's modules. Money and dates travel as strings (Decimal / ISO date).
import type { Role } from '@/auth/context'

export type Customer = {
  id: number
  name: string
  email: string
  phone: string | null
  address: string | null
  has_login: boolean
  created_at: string
}

export type UserRow = { id: number; email: string; name: string; role: Role; created_at: string }

export type Tax = { id: number; name: string; kind: 'PERCENT' | 'FIXED'; rate: string }

export type Variant = { id: number; attribute: string; value: string; extra_price: string }

export type Product = {
  id: number
  name: string
  type: 'SERVICE' | 'GOODS'
  sales_price: string
  cost_price: string
  notes: string | null
  active: boolean
  variants: Variant[]
  default_taxes: Tax[]
  created_at: string
}

export type BillingPeriod = 'DAILY' | 'WEEKLY' | 'MONTHLY' | 'YEARLY'
export const PERIOD_LABEL: Record<BillingPeriod, string> = { DAILY: 'Daily', WEEKLY: 'Weekly', MONTHLY: 'Monthly', YEARLY: 'Yearly' }

export const PERIOD_UNIT: Record<BillingPeriod, string> = { DAILY: 'day', WEEKLY: 'week', MONTHLY: 'month', YEARLY: 'year' }

export type Plan = {
  id: number
  name: string
  price: string
  billing_period: BillingPeriod
  min_quantity: number
  available_from: string | null
  available_to: string | null
  auto_close: boolean
  closable: boolean
  pausable: boolean
  renewable: boolean
  active: boolean
  created_at: string
}

export type SubStatus = 'DRAFT' | 'QUOTATION' | 'CONFIRMED' | 'ACTIVE' | 'PAUSED' | 'CLOSED'
export type Brief = { id: number; name: string }

export type SubListItem = {
  id: number
  number: string
  status: SubStatus
  customer: Brief
  plan: Brief & { billing_period: BillingPeriod }
  start_date: string
  expiry_date: string | null
  total: string
}

export type SubLine = {
  id: number
  product_id: number
  product_name: string
  variant_id: number | null
  variant_label: string | null
  quantity: number
  unit_price: string
  subtotal: string
  tax_amount: string
  amount: string
  taxes: Tax[]
}

export type SubEvent = {
  id: number
  from_status: SubStatus | null
  to_status: SubStatus
  reason: string | null
  actor_name: string | null
  created_at: string
}

export type PlanInfo = Brief & {
  billing_period: BillingPeriod
  min_quantity: number
  pausable: boolean
  closable: boolean
  renewable: boolean
  auto_close: boolean
}

/** What a customer sees. `allowed_actions` = target statuses plus "RENEW", already filtered by plan flags. */
export type PortalSubscription = {
  id: number
  number: string
  status: SubStatus
  customer: Brief & { email: string }
  plan: PlanInfo
  start_date: string
  expiry_date: string | null
  payment_term_days: number
  quotation_valid_until: string | null
  next_invoice_date: string | null
  created_at: string
  lines: SubLine[]
  subtotal: string
  tax_total: string
  total: string
  events: SubEvent[]
  allowed_actions: string[]
}

export type Subscription = PortalSubscription & {
  validity_days: number
  notes: string | null
  created_by: string | null
  editable: boolean
}

export type TemplateLine = {
  id: number
  product_id: number
  product_name: string
  variant_id: number | null
  variant_label: string | null
  quantity: number
}

export type Template = {
  id: number
  name: string
  plan: Brief & { billing_period: BillingPeriod }
  validity_days: number
  notes: string | null
  lines: TemplateLine[]
  created_at: string
}

export type PricePreview = { unit_price: string; subtotal: string; discount_amount: string; tax_amount: string; total: string }
