import clsx from 'clsx'
import type { InputHTMLAttributes, ReactNode, SelectHTMLAttributes, TextareaHTMLAttributes } from 'react'

const control =
  'rounded-md border bg-white px-3 text-sm outline-none focus:border-brand focus:ring-2 focus:ring-brand/20 disabled:bg-surface disabled:text-muted'

// Full width by default; an explicit `w-*` class (e.g. a filter dropdown) wins. `max-w-*` doesn't count.
const fullWidth = (className?: string) => (/(^|\s)w-/.test(className ?? '') ? '' : 'w-full')

/** Label + control + inline error. `error` is usually `err.fields.<name>` from ApiError. */
export function FormField({
  label,
  htmlFor,
  error,
  hint,
  className,
  children,
}: {
  label: string
  htmlFor: string
  error?: string
  hint?: string
  className?: string
  children: ReactNode
}) {
  return (
    <div className={clsx('grid content-start gap-1.5', className)}>
      <label htmlFor={htmlFor} className="text-sm font-medium">
        {label}
      </label>
      {children}
      {error ? <p className="text-xs text-danger">{error}</p> : hint ? <p className="text-xs text-muted">{hint}</p> : null}
    </div>
  )
}

export function Input({ error, className, ...props }: InputHTMLAttributes<HTMLInputElement> & { error?: boolean }) {
  return <input className={clsx(control, fullWidth(className), 'h-9', error ? 'border-danger' : 'border-line', className)} {...props} />
}

export function Select({ error, className, ...props }: SelectHTMLAttributes<HTMLSelectElement> & { error?: boolean }) {
  return <select className={clsx(control, fullWidth(className), 'h-9', error ? 'border-danger' : 'border-line', className)} {...props} />
}

export function Textarea({ error, className, ...props }: TextareaHTMLAttributes<HTMLTextAreaElement> & { error?: boolean }) {
  return <textarea className={clsx(control, fullWidth(className), 'min-h-20 py-2', error ? 'border-danger' : 'border-line', className)} {...props} />
}

export function Checkbox({ label, hint, ...props }: Omit<InputHTMLAttributes<HTMLInputElement>, 'type'> & { label: string; hint?: string }) {
  return (
    <label className="flex items-start gap-2 text-sm">
      <input type="checkbox" className="mt-0.5 size-4 accent-[var(--color-brand)]" {...props} />
      <span>
        <span className="font-medium">{label}</span>
        {hint && <span className="block text-xs text-muted">{hint}</span>}
      </span>
    </label>
  )
}

export function Alert({ kind = 'error', children }: { kind?: 'error' | 'success' | 'info'; children: ReactNode }) {
  return (
    <p
      role={kind === 'error' ? 'alert' : 'status'}
      className={clsx(
        'rounded-md border px-3 py-2 text-sm',
        kind === 'error' && 'border-danger/30 bg-danger/5 text-danger',
        kind === 'success' && 'border-green-600/30 bg-green-600/5 text-green-800',
        kind === 'info' && 'border-line bg-surface text-muted',
      )}
    >
      {children}
    </p>
  )
}
