import { Checkbox } from './forms'

export type CheckOption = { id: number; label: string }

/** A scrollable list of checkboxes that edits a list of selected ids. */
export function CheckList({ options, selected, onChange, empty = 'Nothing to choose from.' }: { options: CheckOption[]; selected: number[]; onChange: (ids: number[]) => void; empty?: string }) {
  const toggle = (id: number, checked: boolean) => onChange(checked ? [...selected, id] : selected.filter((x) => x !== id))
  if (options.length === 0) return <p className="text-sm text-muted">{empty}</p>
  return (
    <div className="grid max-h-56 gap-2 overflow-auto rounded-md border border-line p-3">
      {options.map((option) => (
        <Checkbox key={option.id} label={option.label} checked={selected.includes(option.id)} onChange={(e) => toggle(option.id, e.target.checked)} />
      ))}
    </div>
  )
}
