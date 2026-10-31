import type { ReactNode } from 'react'

/** The one look for every signed-out page (sign in, sign up, forgot, reset, choose a password). */
export function AuthPanel({ eyebrow, title, subtitle, children, footer }: { eyebrow: string; title: string; subtitle?: string; children: ReactNode; footer?: ReactNode }) {
  return (
    <div>
      <p className="text-[10px] font-medium uppercase tracking-[0.22em] text-brand">{eyebrow}</p>
      <h1 className="mt-2 text-[28px] font-medium tracking-[-0.045em]">{title}</h1>
      {subtitle && <p className="mt-2 text-[13px] text-muted">{subtitle}</p>}
      <div className="mt-7 grid gap-4">{children}</div>
      {footer && <div className="mt-5 flex flex-wrap justify-between gap-2 text-[12px]">{footer}</div>}
    </div>
  )
}
