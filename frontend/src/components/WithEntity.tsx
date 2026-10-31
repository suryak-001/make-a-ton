import { useQuery } from '@tanstack/react-query'
import type { ReactNode } from 'react'
import { api, ApiError } from '@/lib/api'
import { Alert } from './forms'

/** Loads `path/id` for an edit page and renders `children(record)`; with no `id` it renders `children()` for a new record. */
export function WithEntity<T>({ id, path, label, children }: { id?: string; path: string; label: string; children: (record?: T) => ReactNode }) {
  const record = useQuery({ queryKey: [path, id], queryFn: () => api.get<T>(`${path}/${id}`), enabled: !!id })
  if (id && record.isPending) return <p className="text-sm text-muted">Loading…</p>
  if (id && record.isError) return <Alert>{record.error instanceof ApiError ? record.error.message : `Could not load the ${label}.`}</Alert>
  return <>{children(record.data)}</>
}
