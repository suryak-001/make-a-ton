import clsx from 'clsx'

export function buttonClass(variant: 'primary' | 'outline' | 'ghost' = 'primary', className?: string) {
  return clsx(
    'inline-flex h-9 shrink-0 items-center justify-center whitespace-nowrap rounded-md px-3 text-sm font-medium transition disabled:opacity-50',
    variant === 'primary' && 'bg-brand text-brand-fg hover:opacity-90',
    variant === 'outline' && 'border border-line bg-white hover:bg-surface',
    variant === 'ghost' && 'hover:bg-surface',
    className,
  )
}
