export const CURRENCY = 'INR'

export function money(value: number | string | null | undefined) {
  return new Intl.NumberFormat('en-IN', { style: 'currency', currency: CURRENCY }).format(Number(value ?? 0))
}

/** Accepts API dates (`YYYY-MM-DD`) or ISO timestamps. */
export function formatDate(value: string | null | undefined) {
  if (!value) return '—'
  return new Intl.DateTimeFormat('en-IN', { dateStyle: 'medium', timeZone: 'UTC' }).format(new Date(value))
}

/** "12 Jan 2026 → open-ended" / "Always" for a plan's availability window. */
export function availability(plan: { available_from: string | null; available_to: string | null }) {
  if (!plan.available_from && !plan.available_to) return 'Always'
  return `${plan.available_from ? formatDate(plan.available_from) : 'Any time'} → ${plan.available_to ? formatDate(plan.available_to) : 'open-ended'}`
}

export function formatDateTime(value: string | null | undefined) {
  if (!value) return '—'
  return new Intl.DateTimeFormat('en-IN', { dateStyle: 'medium', timeStyle: 'short' }).format(new Date(value))
}

/** Today as `YYYY-MM-DD` in the user's own time zone (what a date input expects). */
export function todayISO() {
  const d = new Date()
  const pad = (n: number) => String(n).padStart(2, '0')
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`
}

/** "Monthly" stays "Monthly"; "Pro" on a yearly plan becomes "Pro · Yearly". */
export function planLabel(plan: { name: string; billing_period: string }) {
  const period = plan.billing_period.charAt(0) + plan.billing_period.slice(1).toLowerCase()
  return plan.name.toLowerCase().includes(plan.billing_period.toLowerCase().replace(/ly$/, '')) ? plan.name : `${plan.name} · ${period}`
}
