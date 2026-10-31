import { useQuery } from '@tanstack/react-query'
import { useState } from 'react'
import { api, type Page, qs } from '@/lib/api'
import { useDebounced } from '@/lib/hooks'
import type { Brief, Customer } from '@/lib/types'
import { Input } from './forms'

/** Search-as-you-type customer chooser (works with thousands of customers). */
export function CustomerPicker({
  id,
  value,
  onChange,
  error,
}: {
  id: string
  value: Brief | null
  onChange: (customer: Brief) => void
  error?: boolean
}) {
  const [text, setText] = useState('')
  const [open, setOpen] = useState(false)
  const q = useDebounced(text, 250)
  const results = useQuery({
    queryKey: ['customers', 'picker', q],
    queryFn: () => api.get<Page<Customer>>(`/customers${qs({ q, page_size: 8 })}`),
    enabled: open,
  })

  return (
    <div className="relative">
      <Input
        id={id}
        role="combobox"
        aria-expanded={open}
        aria-controls={`${id}-list`}
        autoComplete="off"
        placeholder="Search customers…"
        value={open ? text : (value?.name ?? '')}
        onFocus={() => {
          setText('')
          setOpen(true)
        }}
        onBlur={() => setOpen(false)}
        onKeyDown={(e) => e.key === 'Escape' && setOpen(false)}
        onChange={(e) => setText(e.target.value)}
        error={error}
      />
      {open && (
        <ul id={`${id}-list`} role="listbox" className="absolute z-10 mt-1 max-h-60 w-full overflow-auto rounded-md border border-line bg-white py-1 shadow-lg">
          {results.isPending ? (
            <li className="px-3 py-2 text-sm text-muted">Searching…</li>
          ) : results.data?.items.length ? (
            results.data.items.map((c) => (
              <li
                key={c.id}
                role="option"
                aria-selected={value?.id === c.id}
                // onMouseDown (not onClick) so it fires before the input's blur closes the list
                onMouseDown={(e) => {
                  e.preventDefault()
                  onChange({ id: c.id, name: c.name })
                  setOpen(false)
                }}
                className="cursor-pointer px-3 py-2 text-sm hover:bg-surface"
              >
                <span className="font-medium">{c.name}</span>
                <span className="ml-2 text-muted">{c.email}</span>
              </li>
            ))
          ) : (
            <li className="px-3 py-2 text-sm text-muted">No customers found.</li>
          )}
        </ul>
      )}
    </div>
  )
}
