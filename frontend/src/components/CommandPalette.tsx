import { useEffect, useMemo, useRef, useState } from 'react'
import { useNavigate } from 'react-router'
import { Search } from 'lucide-react'
import type { NavItem } from '@/nav'
import { BrandMark } from './BrandMark'

export function CommandPalette({ items }: { items: NavItem[] }) {
  const [open, setOpen] = useState(false)
  const [query, setQuery] = useState('')
  const inputRef = useRef<HTMLInputElement>(null)
  const navigate = useNavigate()

  useEffect(() => {
    const onKeyDown = (event: KeyboardEvent) => {
      if ((event.metaKey || event.ctrlKey) && event.key.toLowerCase() === 'k') {
        event.preventDefault()
        setQuery('')
        setOpen((value) => !value)
      }
      if (event.key === 'Escape') setOpen(false)
    }
    window.addEventListener('keydown', onKeyDown)
    return () => window.removeEventListener('keydown', onKeyDown)
  }, [])

  useEffect(() => {
    if (!open) return
    requestAnimationFrame(() => inputRef.current?.focus())
  }, [open])

  const results = useMemo(() => {
    const needle = query.trim().toLowerCase()
    return needle ? items.filter((item) => `${item.label} ${item.href}`.toLowerCase().includes(needle)) : items
  }, [items, query])

  const choose = (href: string) => {
    setOpen(false)
    navigate(href)
  }

  return (
    <>
      <button
        type="button"
        onClick={() => { setQuery(''); setOpen(true) }}
        className="hidden h-8 min-w-52 items-center justify-between border border-line bg-paper px-2.5 text-[12px] text-muted transition hover:border-ink md:flex"
      >
        <span className="flex items-center gap-2"><Search className="size-3.5" /> Search workspace</span>
        <kbd className="border border-line bg-surface px-1.5 py-0.5 font-sans text-[10px] text-ink">⌘ K</kbd>
      </button>
      <button type="button" onClick={() => { setQuery(''); setOpen(true) }} className="grid size-9 place-items-center rounded-md border border-line text-muted hover:bg-surface hover:text-ink md:hidden" aria-label="Search workspace"><Search className="size-4" /></button>
      {open && (
        <div className="fixed inset-0 z-50 flex items-start justify-center bg-ink/55 px-4 pt-[12vh] backdrop-blur-[2px]" onMouseDown={() => setOpen(false)}>
          <section
            role="dialog"
            aria-modal="true"
            aria-label="Command palette"
            className="page-enter w-full max-w-xl border border-ink bg-paper shadow-[7px_7px_0_#171713]"
            onMouseDown={(event) => event.stopPropagation()}
          >
            <div className="flex items-center gap-3 border-b border-ink p-3">
              <BrandMark compact />
              <input
                ref={inputRef}
                value={query}
                onChange={(event) => setQuery(event.target.value)}
                onKeyDown={(event) => {
                  if (event.key === 'Enter' && results[0]) choose(results[0].href)
                }}
                placeholder="Go to a page…"
                className="h-9 min-w-0 flex-1 bg-transparent text-[14px] outline-none placeholder:text-muted"
              />
              <kbd className="border border-line px-1.5 py-0.5 text-[10px] text-muted">ESC</kbd>
            </div>
            <div className="max-h-80 overflow-y-auto p-2">
              {results.length ? results.map((item, index) => (
                <button
                  type="button"
                  key={item.href}
                  onClick={() => choose(item.href)}
                  className="group flex w-full items-center gap-3 border border-transparent px-3 py-2 text-left text-[13px] hover:border-ink hover:bg-yellow"
                >
                  <span className="grid size-5 place-items-center border border-current text-[9px] font-medium">{String(index + 1).padStart(2, '0')}</span>
                  <span className="flex-1 font-medium">{item.label}</span>
                  <span className="text-[11px] text-muted group-hover:text-ink">{item.href}</span>
                </button>
              )) : <p className="p-6 text-center text-[13px] text-muted">No matching page</p>}
            </div>
          </section>
        </div>
      )}
    </>
  )
}
