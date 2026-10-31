import clsx from 'clsx'
import { MoreVertical, type LucideIcon } from 'lucide-react'
import { useEffect, useRef, useState } from 'react'
import { createPortal } from 'react-dom'

export type RowAction = { label: string; icon: LucideIcon; onSelect: () => void; danger?: boolean }

/** The same three-dot menu on every list: Edit, Active/Inactive, Delete (plus anything extra a list adds). */
export function RowActions({ actions, label = 'Row actions' }: { actions: RowAction[]; label?: string }) {
  const [at, setAt] = useState<{ top: number; right: number }>()
  const button = useRef<HTMLButtonElement>(null)

  useEffect(() => {
    if (!at) return
    const close = () => setAt(undefined)
    const onKey = (e: KeyboardEvent) => e.key === 'Escape' && close()
    window.addEventListener('scroll', close, true)
    window.addEventListener('resize', close)
    window.addEventListener('keydown', onKey)
    return () => {
      window.removeEventListener('scroll', close, true)
      window.removeEventListener('resize', close)
      window.removeEventListener('keydown', onKey)
    }
  }, [at])

  function toggle(e: React.MouseEvent) {
    e.stopPropagation()
    if (at) return setAt(undefined)
    const rect = button.current!.getBoundingClientRect()
    setAt({ top: rect.bottom + 4, right: window.innerWidth - rect.right })
  }

  return (
    <>
      <button ref={button} type="button" aria-label={label} aria-haspopup="menu" aria-expanded={!!at} onClick={toggle} onKeyDown={(e) => e.stopPropagation()} className="grid size-8 place-items-center rounded-md border border-transparent text-muted transition hover:border-line hover:bg-surface hover:text-ink">
        <MoreVertical className="size-4" />
      </button>
      {at && createPortal(
        <>
          <div className="fixed inset-0 z-[80]" onClick={(e) => { e.stopPropagation(); setAt(undefined) }} />
          <div role="menu" style={{ top: at.top, right: at.right }} className="sheet-enter fixed z-[81] min-w-44 overflow-hidden rounded-md border border-ink bg-paper py-1 shadow-[4px_4px_0_#171713]">
            {actions.map((a) => (
              <button key={a.label} type="button" role="menuitem" onClick={(e) => { e.stopPropagation(); setAt(undefined); a.onSelect() }} className={clsx('flex w-full items-center gap-2.5 px-3 py-2 text-left text-[13px] hover:bg-surface', a.danger ? 'text-danger' : 'text-ink')}>
                <a.icon className="size-4 shrink-0" strokeWidth={1.8} />
                {a.label}
              </button>
            ))}
          </div>
        </>,
        document.body,
      )}
    </>
  )
}
