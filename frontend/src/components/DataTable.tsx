import clsx from 'clsx'
import type { ReactNode } from 'react'
import { Button } from './ui'

export type Column<T> = {
  header: string
  cell: (row: T) => ReactNode
  className?: string // applied to th and td, e.g. 'text-right'
}

export function DataTable<T>({
  columns,
  rows,
  rowKey,
  onRowClick,
  loading,
  empty = 'Nothing here yet.',
  actions,
  flashId,
}: {
  columns: Column<T>[]
  rows: T[] | undefined
  rowKey: (row: T) => string | number
  onRowClick?: (row: T) => void
  loading?: boolean
  empty?: string
  /** Renders the row's ⋯ menu (see RowActions): last cell on a table, top-right of a card. */
  actions?: (row: T) => ReactNode
  /** The row with this key glows briefly (a record that was just saved). */
  flashId?: string
}) {
  return (
    <>
      <div className="overflow-hidden rounded-md border border-line bg-paper md:hidden">
        {loading && !rows ? <p className="px-4 py-10 text-center text-[13px] text-muted">Loading…</p> : rows?.length ? rows.map((row) => (
          <div key={rowKey(row)} onClick={onRowClick && (() => onRowClick(row))} onKeyDown={onRowClick ? (event) => { if (event.key === 'Enter' || event.key === ' ') onRowClick(row) } : undefined} role={onRowClick ? 'button' : undefined} tabIndex={onRowClick ? 0 : undefined} className={clsx('border-b border-line p-5 last:border-b-0', flashId === String(rowKey(row)) && 'row-flash', onRowClick && 'cursor-pointer transition-colors hover:bg-surface focus:bg-surface focus:outline-none')}>
            <div className="mb-3 flex items-start justify-between gap-3"><span className="text-[13px] font-medium">{columns[0]?.cell(row)}</span>{actions ? <span className="-mr-2 -mt-1.5">{actions(row)}</span> : <span className="text-[10px] uppercase tracking-[0.1em] text-muted">{columns[0]?.header}</span>}</div>
            <dl className="grid grid-cols-2 gap-x-5 gap-y-3">{columns.slice(1).map((column) => <div key={column.header} className="min-w-0"><dt className="text-[9px] font-medium uppercase tracking-[0.1em] text-muted">{column.header}</dt><dd className="mt-1 truncate text-[12px] tabular-nums">{column.cell(row)}</dd></div>)}</dl>
          </div>
        )) : <p className="px-4 py-10 text-center text-[13px] text-muted">{empty}</p>}
      </div>
      <div className="hidden overflow-x-auto rounded-md border border-line bg-paper md:block">
      <table className="w-full min-w-[720px] text-left text-[13px] tabular-nums">
        <thead className="border-b border-ink bg-surface text-[10px] uppercase tracking-[0.12em] text-muted">
          <tr>
            {columns.map((c) => (
              <th key={c.header} className={clsx('px-4 py-3 font-medium', c.className)}>
                {c.header}
              </th>
            ))}
            {actions && <th className="w-12 px-3 py-3"><span className="sr-only">Actions</span></th>}
          </tr>
        </thead>
        <tbody className="divide-y divide-line">
          {loading && !rows ? (
            <tr>
              <td colSpan={columns.length + (actions ? 1 : 0)} className="px-4 py-8 text-center text-muted">
                Loading…
              </td>
            </tr>
          ) : rows && rows.length > 0 ? (
            rows.map((row) => (
              <tr
                key={rowKey(row)}
                onClick={onRowClick && (() => onRowClick(row))}
                className={clsx('transition-colors', flashId === String(rowKey(row)) && 'row-flash', onRowClick && 'cursor-pointer hover:bg-yellow/25')}
              >
                {columns.map((c) => (
                  <td key={c.header} className={clsx('px-4 py-3.5', c.className)}>
                    {c.cell(row)}
                  </td>
                ))}
                {actions && <td className="px-2 py-1.5 text-right">{actions(row)}</td>}
              </tr>
            ))
          ) : (
            <tr>
              <td colSpan={columns.length + (actions ? 1 : 0)} className="px-4 py-8 text-center text-muted">
                {empty}
              </td>
            </tr>
          )}
        </tbody>
      </table>
      </div>
    </>
  )
}

export function Pagination({ page, pageSize, total, onPage }: { page: number; pageSize: number; total: number; onPage: (p: number) => void }) {
  const pages = Math.max(1, Math.ceil(total / pageSize))
  if (total <= pageSize) return total ? <p className="mt-3 text-[11px] uppercase tracking-[0.08em] text-muted">{total} total records</p> : null
  const from = (page - 1) * pageSize + 1
  const to = Math.min(page * pageSize, total)
  return (
    <div className="mt-3 flex flex-wrap items-center justify-between gap-3 text-[12px]">
      <p className="text-muted tabular-nums">
        {from}–{to} of {total}
      </p>
      <div className="flex items-center gap-2">
        <Button variant="outline" disabled={page <= 1} onClick={() => onPage(page - 1)}>
          Previous
        </Button>
        <span className="border-x border-line px-3 text-muted tabular-nums">
          Page {page} of {pages}
        </span>
        <Button variant="outline" disabled={page >= pages} onClick={() => onPage(page + 1)}>
          Next
        </Button>
      </div>
    </div>
  )
}
