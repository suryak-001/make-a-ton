import { type ReactNode, useEffect, useRef } from 'react'

/** Native <dialog>: focus trap, Esc to close and backdrop come from the browser. */
export function Modal({ open, onClose, title, status, description, wide, children }: { open: boolean; onClose: () => void; title: string; status?: string; description?: string; wide?: boolean; children: ReactNode }) {
  const ref = useRef<HTMLDialogElement>(null)
  useEffect(() => {
    const el = ref.current
    if (!el) return
    if (open && !el.open) el.showModal()
    if (!open && el.open) el.close()
  }, [open])
  useEffect(() => {
    if (!open) return
    const previous = document.body.style.overflow
    document.body.style.overflow = 'hidden'
    return () => { document.body.style.overflow = previous }
  }, [open])

  return (
    <dialog
      ref={ref}
      onClose={onClose}
      onClick={(e) => e.target === ref.current && onClose()}
      className={`m-auto max-h-[92vh] w-[calc(100%-2rem)] ${wide ? 'max-w-2xl' : 'max-w-lg'} overflow-y-auto border border-ink bg-paper p-0 shadow-[7px_7px_0_#171713]`}
    >
      {open && (
        <div className="page-enter">
          <header className="flex items-start gap-4 border-b border-ink px-5 py-4">
            <div className="min-w-0 flex-1">
              <h2 className="text-[18px] font-medium tracking-[-0.02em]">{title}</h2>
              {description && <p className="mt-1 text-[12px] text-muted">{description}</p>}
            </div>
            {status && <span className="border border-green/30 bg-green/10 px-2 py-1 text-[10px] font-medium uppercase tracking-[0.08em] text-green">{status}</span>}
            <button type="button" onClick={onClose} aria-label="Close modal" className="grid size-8 place-items-center border border-ink bg-paper text-lg hover:bg-yellow">×</button>
          </header>
          <div className="p-5">{children}</div>
        </div>
      )}
    </dialog>
  )
}
