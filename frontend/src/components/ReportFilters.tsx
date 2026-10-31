import { useState } from 'react'
import { usePlans } from '@/lib/queries'
import type { Brief, ReportFilters as Filters } from '@/lib/types'
import { CustomerPicker } from './CustomerPicker'
import { DateField } from './DateField'
import { FormField, Select } from './forms'
import { Button } from './ui'

/** Date range, plan and customer for the finance numbers. */
export function ReportFilters({ values, onChange }: { values: Filters; onChange: (values: Filters) => void }) {
  const plans = usePlans()
  const [customer, setCustomer] = useState<Brief | null>(null)
  const set = (patch: Filters) => onChange({ ...values, ...patch })
  const pickCustomer = (picked: Brief) => {
    setCustomer(picked)
    set({ customer_id: String(picked.id) })
  }
  const clear = () => {
    setCustomer(null)
    onChange({})
  }

  return (
    <div className="mb-5 flex flex-wrap items-end gap-3 rounded-md border border-line bg-paper p-3">
      <DateField id="report-from" label="From" value={values.from_date ?? ''} onChange={(from_date) => set({ from_date })} optional />
      <DateField id="report-to" label="To" value={values.to_date ?? ''} onChange={(to_date) => set({ to_date })} optional />
      <FormField label="Plan" htmlFor="report-plan">
        <Select id="report-plan" value={values.plan_id ?? ''} onChange={(e) => set({ plan_id: e.target.value })} className="w-48">
          <option value="">All plans</option>
          {plans.data?.map((plan) => <option key={plan.id} value={plan.id}>{plan.name}</option>)}
        </Select>
      </FormField>
      <FormField label="Customer" htmlFor="report-customer" className="w-56">
        <CustomerPicker id="report-customer" value={customer} onChange={pickCustomer} />
      </FormField>
      <Button variant="ghost" onClick={clear}>Clear filters</Button>
    </div>
  )
}
