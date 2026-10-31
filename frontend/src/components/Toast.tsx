/* oxlint-disable react/only-export-components */
import { createContext, type ReactNode, useCallback, useContext, useMemo, useRef, useState } from 'react'

type ToastInput = { message: string; actionLabel?: string; onAction?: () => void }
type ToastItem = ToastInput & { id: number }
type ToastContextValue = { toast: (input: string | ToastInput) => void }

const ToastContext = createContext<ToastContextValue | null>(null)

export function ToastProvider({ children }: { children: ReactNode }) {
  const [items, setItems] = useState<ToastItem[]>([])
  const idRef = useRef(0)

  const toast = useCallback((input: string | ToastInput) => {
    const next = typeof input === 'string' ? { message: input } : input
    const id = ++idRef.current
    setItems((current) => current.some((item) => item.message === next.message) ? current : [...current, { ...next, id }])
    window.setTimeout(() => setItems((current) => current.filter((item) => item.id !== id)), 4500)
  }, [])

  const value = useMemo(() => ({ toast }), [toast])
  return (
    <ToastContext.Provider value={value}>
      {children}
      <div className="fixed bottom-4 right-4 z-[70] grid w-[min(360px,calc(100vw-2rem))] gap-2" aria-live="polite">
        {items.map((item) => (
          <div key={item.id} className="sheet-enter flex items-center gap-3 border border-ink bg-ink px-4 py-3 text-[13px] text-paper shadow-[4px_4px_0_#1849d6]">
            <span className="size-2 shrink-0 rounded-full bg-yellow" />
            <span className="flex-1">{item.message}</span>
            {item.actionLabel && <button type="button" className="font-medium text-yellow underline underline-offset-4" onClick={() => { item.onAction?.(); setItems((current) => current.filter((toastItem) => toastItem.id !== item.id)) }}>{item.actionLabel}</button>}
            <button type="button" aria-label="Dismiss notification" className="text-paper/70 hover:text-paper" onClick={() => setItems((current) => current.filter((toastItem) => toastItem.id !== item.id))}>×</button>
          </div>
        ))}
      </div>
    </ToastContext.Provider>
  )
}

export function useToast() {
  const context = useContext(ToastContext)
  if (!context) throw new Error('useToast must be used inside ToastProvider')
  return context
}
