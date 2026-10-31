// Small shared primitives. Add to this file (or a sibling) rather than restyling in each page.
import clsx from 'clsx'
import { buttonClass } from './button-class'
import { useInModal } from './modal-context'
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
      <label htmlFor={id} className="text-[12px] font-medium uppercase tracking-[0.08em] text-muted">
        {label}
      </label>
      <input
        id={id}
        className="h-9 rounded-md border border-line bg-paper px-3 text-[13px] outline-none focus:border-brand focus:shadow-[0_0_0_2px_rgb(24_73_214_/_0.14)]"
        {...props}
      />
    </div>
  )
}

export function Card({ className, ...props }: HTMLAttributes<HTMLDivElement>) {
  return <div className={clsx('rounded-md border border-line bg-paper', className)} {...props} />
}

export function Badge({ children, className }: { children: ReactNode; className?: string }) {
  return (
    <span className={clsx('inline-flex items-center border border-line px-2 py-0.5 text-[11px] font-medium uppercase tracking-[0.06em]', className)}>
      {children}
    </span>
  )
}

export function PageHeader({ title, description, actions }: { title: string; description?: string; actions?: ReactNode }) {
  if (useInModal()) return null // the pop-up has its own title
  return (
    <div className="mb-5 flex flex-wrap items-end justify-between gap-4 border-b border-line pb-4">
      <div>
        <h1 className="text-[22px] font-medium leading-tight tracking-[-0.03em]">{title}</h1>
        {description && <p className="mt-1 max-w-2xl text-[13px] text-muted">{description}</p>}
      </div>
      {actions && <div className="flex w-full flex-wrap gap-2 sm:w-auto sm:shrink-0">{actions}</div>}
    </div>
  )
}
