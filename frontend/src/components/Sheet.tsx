import { type ReactNode, useEffect, useRef } from 'react'

export function Sheet({ open, onClose, title, subtitle, children }: { open: boolean; onClose: () => void; title: string; subtitle?: string; children: ReactNode }) {
  const ref = useRef<HTMLDialogElement>(null)
  useEffect(() => {
    const element = ref.current
    if (!element) return
    if (open && !element.open) element.showModal()
    if (!open && element.open) element.close()
  }, [open])

  useEffect(() => {
    if (!open) return
    const previous = document.body.style.overflow
    document.body.style.overflow = 'hidden'
    return () => { document.body.style.overflow = previous }
  }, [open])

  return (
    <dialog ref={ref} onClose={onClose} onClick={(event) => event.target === ref.current && onClose()} className="m-0 ml-auto h-full max-h-none w-full max-w-2xl border-0 border-l border-ink bg-paper p-0 shadow-[-8px_0_0_rgb(23_23_19_/_0.12)]">
      {open && <div className="sheet-enter flex min-h-full flex-col">
        <header className="sticky top-0 z-10 flex items-start gap-4 border-b border-ink bg-paper px-5 py-4">
          <div className="min-w-0 flex-1">
            <p className="text-[9px] font-medium uppercase tracking-[0.2em] text-brand">Quick detail</p>
            <h2 className="mt-1 truncate text-[18px] font-medium tracking-[-0.02em]">{title}</h2>
            {subtitle && <p className="mt-0.5 text-[12px] text-muted">{subtitle}</p>}
          </div>
          <button type="button" onClick={onClose} aria-label="Close panel" className="grid size-9 place-items-center border border-ink bg-paper text-xl transition hover:bg-yellow">×</button>
        </header>
        <div className="min-h-0 flex-1 overflow-y-auto p-5">{children}</div>
      </div>}
    </dialog>
  )
}
