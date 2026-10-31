import clsx from 'clsx'
import { Check, ChevronDown } from 'lucide-react'
import { useEffect, useState } from 'react'

/** Status badge that is also the switch: pick Active or Inactive right in the list, it saves at once. */
export function StatusSelect({ active, onChange, disabled }: { active: boolean; onChange: (active: boolean) => void; disabled?: boolean }) {
  const [saved, setSaved] = useState(false)
  useEffect(() => {
    if (!saved) return
    const t = window.setTimeout(() => setSaved(false), 1400)
    return () => window.clearTimeout(t)
  }, [saved])

  const tone = active ? 'border-green/30 bg-green/10 text-green' : 'border-line bg-surface text-muted'
  if (disabled) return <span className={clsx('inline-flex items-center border px-2 py-0.5 text-[11px] font-medium uppercase tracking-[0.06em]', tone)}>{active ? 'Active' : 'Inactive'}</span>
  return (
    <span className="relative inline-flex items-center" onClick={(e) => e.stopPropagation()}>
      <select
        aria-label="Status"
        value={active ? 'true' : 'false'}
        onChange={(e) => { onChange(e.target.value === 'true'); setSaved(true) }}
        onKeyDown={(e) => e.stopPropagation()}
        className={clsx('cursor-pointer appearance-none rounded-sm border py-0.5 pl-2 pr-6 text-[11px] font-medium uppercase tracking-[0.06em] outline-none focus:border-brand', tone)}
      >
        <option value="true">Active</option>
        <option value="false">Inactive</option>
      </select>
      {saved ? <Check className="pointer-events-none absolute right-1.5 size-3 animate-[pop_300ms_ease-out]" /> : <ChevronDown className="pointer-events-none absolute right-1.5 size-3 opacity-60" />}
    </span>
  )
}
