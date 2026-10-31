export const CURRENCY = 'INR'

export function money(value: number | string | null | undefined) {
  return new Intl.NumberFormat('en-IN', { style: 'currency', currency: CURRENCY }).format(Number(value ?? 0))
}

/** Accepts API dates (`YYYY-MM-DD`) or ISO timestamps. */
export function formatDate(value: string | null | undefined) {
  if (!value) return '—'
  return new Intl.DateTimeFormat('en-IN', { dateStyle: 'medium', timeZone: 'UTC' }).format(new Date(value))
}
