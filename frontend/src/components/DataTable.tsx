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
}: {
  columns: Column<T>[]
  rows: T[] | undefined
  rowKey: (row: T) => string | number
  onRowClick?: (row: T) => void
  loading?: boolean
  empty?: string
}) {
  return (
    <div className="overflow-x-auto rounded-xl border border-line">
      <table className="w-full text-left text-sm">
        <thead className="bg-surface text-xs uppercase tracking-wide text-muted">
          <tr>
            {columns.map((c) => (
              <th key={c.header} className={clsx('px-4 py-2.5 font-medium', c.className)}>
                {c.header}
              </th>
            ))}
          </tr>
        </thead>
        <tbody className="divide-y divide-line">
          {loading && !rows ? (
            <tr>
              <td colSpan={columns.length} className="px-4 py-8 text-center text-muted">
                Loading…
              </td>
            </tr>
          ) : rows && rows.length > 0 ? (
            rows.map((row) => (
              <tr
                key={rowKey(row)}
                onClick={onRowClick && (() => onRowClick(row))}
                className={clsx(onRowClick && 'cursor-pointer hover:bg-surface')}
              >
                {columns.map((c) => (
                  <td key={c.header} className={clsx('px-4 py-3', c.className)}>
                    {c.cell(row)}
                  </td>
                ))}
              </tr>
            ))
          ) : (
            <tr>
              <td colSpan={columns.length} className="px-4 py-8 text-center text-muted">
                {empty}
              </td>
            </tr>
          )}
        </tbody>
      </table>
    </div>
  )
}

export function Pagination({ page, pageSize, total, onPage }: { page: number; pageSize: number; total: number; onPage: (p: number) => void }) {
  const pages = Math.max(1, Math.ceil(total / pageSize))
  if (total <= pageSize) return total ? <p className="mt-3 text-xs text-muted">{total} total</p> : null
  const from = (page - 1) * pageSize + 1
  const to = Math.min(page * pageSize, total)
  return (
    <div className="mt-3 flex items-center justify-between text-sm">
      <p className="text-muted">
        {from}–{to} of {total}
      </p>
      <div className="flex items-center gap-2">
        <Button variant="outline" disabled={page <= 1} onClick={() => onPage(page - 1)}>
          Previous
        </Button>
        <span className="text-muted">
          Page {page} of {pages}
        </span>
        <Button variant="outline" disabled={page >= pages} onClick={() => onPage(page + 1)}>
          Next
        </Button>
      </div>
    </div>
  )
}
