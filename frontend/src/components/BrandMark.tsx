export function BrandMark({ compact = false }: { compact?: boolean }) {
  return (
    <div className="flex items-center gap-3" aria-label="Brightloop">
      <span className="relative grid size-8 shrink-0 grid-cols-2 overflow-hidden border border-ink bg-paper" aria-hidden="true">
        <span className="bg-brand" />
        <span className="rounded-bl-full bg-yellow" />
        <span className="rounded-tr-full bg-danger" />
        <span className="bg-ink" />
      </span>
      {!compact && (
        <span>
          <span className="block text-[14px] font-medium leading-none tracking-[-0.03em]">brightloop</span>
          <span className="mt-1 block text-[8px] font-medium uppercase tracking-[0.24em] text-muted">operations</span>
        </span>
      )}
    </div>
  )
}
