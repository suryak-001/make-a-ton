import type { InvoiceFilterValues } from '@/lib/invoices'
import { CustomerPicker } from './CustomerPicker'
import { DateField } from './DateField'
import { Checkbox, FormField, Select } from './forms'
import { Button } from './ui'

/** Filters for the invoice list. Every change goes to `onChange` as a partial update. */
export function InvoiceFilters({ values, onChange, onClear }: { values: InvoiceFilterValues; onChange: (patch: Partial<InvoiceFilterValues>) => void; onClear: () => void }) {
  return (
    <div className="mb-4 flex flex-wrap items-end gap-3 rounded-md border border-line bg-paper p-3">
      <FormField label="Status" htmlFor="invoice-status">
        <Select id="invoice-status" value={values.status} onChange={(e) => onChange({ status: e.target.value })} className="w-44">
          <option value="">All statuses</option>
          <option value="DRAFT">Draft</option>
          <option value="CONFIRMED">Confirmed</option>
          <option value="PAID">Paid</option>
          <option value="CANCELLED">Cancelled</option>
        </Select>
      </FormField>
      <FormField label="Customer" htmlFor="invoice-customer" className="w-56">
        <CustomerPicker id="invoice-customer" value={values.customer} onChange={(customer) => onChange({ customer })} />
      </FormField>
      <DateField id="invoice-from" label="From" value={values.from} onChange={(from) => onChange({ from })} optional />
      <DateField id="invoice-to" label="To" value={values.to} onChange={(to) => onChange({ to })} optional />
      <div className="pb-2">
        <Checkbox label="Overdue only" checked={values.overdue} onChange={(e) => onChange({ overdue: e.target.checked })} />
      </div>
      <Button variant="ghost" onClick={onClear}>Clear filters</Button>
    </div>
  )
}
