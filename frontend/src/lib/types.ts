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

export type UserRow = { id: number; email: string; name: string; role: Role; created_at: string; is_active: boolean }

export type Tax = { id: number; name: string; kind: 'PERCENT' | 'FIXED'; rate: string }
/** A tax rule as the Taxes screens see it (a product's `default_taxes` only carry the part above). */
export type TaxRule = Tax & { active: boolean; created_at: string }

export type Variant = { id: number; attribute: string; value: string; extra_price: string }

export type Product = {
  id: number
  name: string
  type: 'SERVICE' | 'GOODS'
  sales_price: string
  cost_price: string
  notes: string | null
  active: boolean
  is_addon: boolean
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
  is_addon: boolean
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

export type InvoiceStatus = 'DRAFT' | 'CONFIRMED' | 'PAID' | 'CANCELLED'
/** What the server allows right now; the buttons are drawn from this list. */
export type InvoiceAction = 'confirm' | 'cancel' | 'pay' | 'send' | 'print' | 'rebill'
export type InvoiceLine = {
  id: number
  product_id: number | null
  description: string
  quantity: number
  unit_price: string
  discount_amount: string
  tax_rate: string
  tax_amount: string
  total: string
}
export type Invoice = {
  id: number
  number: string | null
  status: InvoiceStatus
  subscription: { id: number; number: string }
  customer: { id: number; name: string; email: string }
  period_start: string
  period_end: string
  invoice_date: string
  due_date: string
  subtotal: string
  discount_total: string
  tax_total: string
  total: string
  amount_paid: string
  outstanding: string
  overdue: boolean
  sent_at: string | null
  created_at: string
  allowed_actions: InvoiceAction[]
  lines: InvoiceLine[]
}

export type Discount = {
  id: number
  name: string
  kind: 'PERCENT' | 'FIXED'
  value: string
  min_purchase: string | null
  min_quantity: number | null
  start_date: string
  end_date: string | null
  usage_limit: number | null
  used_count: number
  scope: 'PRODUCT' | 'SUBSCRIPTION'
  active: boolean
  product_ids: number[]
  subscription_ids: number[]
  created_at: string
}

export type Payment = {
  id: number
  invoice_id: number
  invoice_number: string | null
  customer_name: string
  method: 'CASH' | 'BANK_TRANSFER' | 'CARD' | 'UPI' | 'CHEQUE' | 'OTHER'
  amount: string
  payment_date: string
  note: string | null
  recorded_by: string | null
  created_at: string
}

export type Summary = {
  active_subscriptions: number
  mrr: string
  invoiced: string
  collected: string
  outstanding: string
  overdue_count: number
  overdue_amount: string
}

export type RevenuePoint = { month: string; invoiced: string; collected: string }

export type BillingRun = {
  as_of: string
  due: number
  created: number
  already_billed: number
  skipped: number
  failed: number
  errors: { subscription_id: number; period_start: string; error: string }[]
}

export type ReportFilters = { from_date?: string; to_date?: string; plan_id?: string; customer_id?: string }

/** An add-on product and, when it is switched on for this subscription, its line. */
export type AddonOption = {
  product_id: number
  name: string
  notes: string | null
  unit_price: string
  taxes: string[]
  variants: { id: number; label: string; extra_price: string }[]
  line_id: number | null
  quantity: number | null
}
export type Addons = { editable: boolean; blocker: string | null; min_quantity: number; options: AddonOption[] }

export type TimelineItem = {
  at: string
  kind: 'subscription' | 'invoice' | 'payment'
  title: string
  detail: string | null
  amount: string | null
  link: string
}

export type CustomerOverview = {
  customer: Customer
  summary: Summary
  average_days_late: string | null
  subscriptions: SubListItem[]
  invoices: Invoice[]
  payments: Payment[]
  timeline: TimelineItem[]
}

export type StatementRow = {
  ref: string
  line: number
  date: string
  description: string
  amount: string
  method: Payment['method']
  status: 'matched' | 'unmatched' | 'already_recorded'
  confidence: 'high' | 'medium' | 'low' | null
  reason: string
  invoice: { id: number; number: string; customer_name: string; outstanding: string; due_date: string } | null
}
export type StatementPreview = { rows: StatementRow[]; debits_skipped: number; problems: { line: number; error: string }[] }
export type ReconcileResult = {
  recorded: number
  already_recorded: number
  failed: number
  amount_recorded: string
  results: { ref: string; status: 'recorded' | 'already_recorded' | 'failed'; message: string; invoice_number: string | null; outstanding: string | null }[]
}

export type AgingBucket = { key: string; label: string; count: number; amount: string }

export type Proof = {
  subscriptions: number
  invoices: number
  payments: number
  customers: number
  duplicate_invoice_periods: number
  last_invoice_at: string | null
  measured_ms: number
}

export type SetupStep = { key: string; title: string; cta: string; href: string; done: boolean }

export type WorkQueue = {
  draft_invoices: number
  overdue_invoices: number
  renewals_due: { id: number; number: string; customer: string; plan: string; expiry_date: string; days_left: number; renewable: boolean; auto_close: boolean }[]
  quotes_expiring: { id: number; number: string; customer: string; valid_until: string; days_left: number }[]
  to_chase: { id: number; number: string | null; customer: string; due_date: string; days_overdue: number; outstanding: string; stage: string; reminded: boolean; last_reminder_at: string | null }[]
}

export type PortalHome = {
  name: string
  outstanding: string
  overdue_count: number
  overdue_amount: string
  next_due: Invoice | null
  alerts: { kind: 'danger' | 'warning' | 'success'; text: string; href: string | null }[]
  subscriptions: { id: number; number: string; status: SubStatus; plan: string; billing_period: string; total: string; next_invoice_date: string | null; expiry_date: string | null; allowed_actions: string[] }[]
  recent_invoices: Invoice[]
}
