// Small shared primitives. Add to this file (or a sibling) rather than restyling in each page.
import clsx from 'clsx'
import { buttonClass } from './button-class'
import type { ButtonHTMLAttributes, HTMLAttributes, InputHTMLAttributes, ReactNode } from 'react'

export function Button({
  variant = 'primary',
  className,
  ...props
}: ButtonHTMLAttributes<HTMLButtonElement> & { variant?: 'primary' | 'outline' | 'ghost' }) {
  return (
    <button
      className={buttonClass(variant, className)}
      {...props}
    />
  )
}

export function Field({ label, id, ...props }: InputHTMLAttributes<HTMLInputElement> & { label: string; id: string }) {
  return (
    <div className="grid gap-1.5">
      <label htmlFor={id} className="text-sm font-medium">
        {label}
      </label>
      <input
        id={id}
        className="h-9 rounded-md border border-line bg-white px-3 text-sm outline-none focus:border-brand focus:ring-2 focus:ring-brand/20"
        {...props}
      />
    </div>
  )
}

export function Card({ className, ...props }: HTMLAttributes<HTMLDivElement>) {
  return <div className={clsx('rounded-xl border border-line bg-white', className)} {...props} />
}

export function Badge({ children, className }: { children: ReactNode; className?: string }) {
  return (
    <span className={clsx('inline-flex items-center rounded-full border border-line px-2 py-0.5 text-xs font-medium', className)}>
      {children}
    </span>
  )
}

export function PageHeader({ title, description, actions }: { title: string; description?: string; actions?: ReactNode }) {
  return (
    <div className="mb-6 flex items-start justify-between gap-4">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight">{title}</h1>
        {description && <p className="mt-1 text-sm text-muted">{description}</p>}
      </div>
      {actions && <div className="flex shrink-0 gap-2">{actions}</div>}
    </div>
  )
}
