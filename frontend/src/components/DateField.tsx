import { Input } from './forms'

export function DateField({ value, onChange, optional = false, id, label }: { value: string; onChange: (value: string) => void; optional?: boolean; id: string; label: string }) {
  return <div>
    <label className="mb-1 block text-[11px] font-medium uppercase tracking-[0.08em] text-muted" htmlFor={id}>{label}</label>
    <div className="flex">
      <Input id={id} type="date" value={value} onChange={(event) => onChange(event.target.value)} className="w-44" />
      {optional && value && <button type="button" className="border border-l-0 border-line bg-paper px-2 text-[11px] text-muted hover:bg-yellow hover:text-ink" onClick={() => onChange('')}>Clear</button>}
    </div>
  </div>
}
