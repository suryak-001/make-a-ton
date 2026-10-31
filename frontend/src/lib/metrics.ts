/** Plain-language definitions shown beside the finance numbers, so nobody has to guess what a figure includes. */
export const METRIC_DEFINITIONS = {
  active: 'Subscriptions in the Active state right now. Paused and closed ones are not counted.',
  mrr: 'Monthly recurring revenue: every line of every active subscription converted to a monthly amount (yearly ÷ 12, weekly × 4.345, daily × 30). Excludes tax and is before discounts.',
  invoiced: 'Total of Confirmed and Paid invoices dated in the period, including tax. Drafts and cancelled invoices are left out.',
  collected: 'Payments received in the period, whichever invoice they were for.',
  outstanding: 'What is still owed on Confirmed invoices in the period: invoice total minus payments received.',
  overdue: 'Confirmed invoices past their due date that still have a balance. Always as of today, so the date range does not change it.',
} as const

export type MetricKey = keyof typeof METRIC_DEFINITIONS
