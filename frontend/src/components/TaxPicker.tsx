import { useTaxes } from '@/lib/queries'
import { taxRateLabel } from '@/lib/tax'
import { CheckList } from './CheckList'

/** Chooses which active taxes a product carries by default. */
export function TaxPicker({ selected, onChange }: { selected: number[]; onChange: (ids: number[]) => void }) {
  const taxes = useTaxes()
  const options = (taxes.data ?? []).map((tax) => ({ id: tax.id, label: `${tax.name} (${taxRateLabel(tax)})` }))
  return <CheckList options={options} selected={selected} onChange={onChange} empty={taxes.isPending ? 'Loading taxes…' : 'No active taxes yet. An admin can add them on the Taxes page.'} />
}
