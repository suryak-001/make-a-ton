import clsx from 'clsx'

export function buttonClass(variant: 'primary' | 'outline' | 'ghost' = 'primary', className?: string) {
  return clsx(
    'inline-flex h-9 shrink-0 items-center justify-center whitespace-nowrap rounded-md border px-3 text-[13px] font-medium transition-colors duration-150 disabled:cursor-not-allowed disabled:opacity-40',
    variant === 'primary' && 'border-brand bg-brand text-brand-fg hover:bg-brand/90',
    variant === 'outline' && 'border-line bg-paper text-ink hover:border-ink/30 hover:bg-surface',
    variant === 'ghost' && 'border-transparent text-muted hover:bg-ink/5 hover:text-ink',
    className,
  )
}
