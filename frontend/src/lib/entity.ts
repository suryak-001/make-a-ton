import { useMutation, useQueryClient } from '@tanstack/react-query'
import { useState } from 'react'
import { api, ApiError } from './api'

/**
 * Create, update and delete for one kind of record (`path` is e.g. '/taxes'). On success the cached lists
 * and records under `path` are refreshed and `onDone` runs; on failure `error` holds the server's message
 * and its per-field messages (`error.fields`).
 */
export function useEntityMutations<Out>(path: string, onDone: () => void) {
  const queryClient = useQueryClient()
  const [error, setError] = useState<ApiError>()

  const finish = () => {
    queryClient.invalidateQueries({ queryKey: [path] })
    onDone()
  }
  const fail = (e: unknown) => setError(e instanceof ApiError ? e : new ApiError(0, 'Something went wrong. Try again.'))

  const save = useMutation({
    mutationFn: ({ id, body }: { id?: number; body: unknown }) => (id ? api.put<Out>(`${path}/${id}`, body) : api.post<Out>(path, body)),
    onSuccess: finish,
    onError: fail,
  })
  const remove = useMutation({ mutationFn: (id: number) => api.delete(`${path}/${id}`), onSuccess: finish, onError: fail })

  return { save, remove, error, clearError: () => setError(undefined) }
}

/** The message to show above the form: errors tied to a form field are shown beside that field instead. */
export function generalMessage(error: ApiError | undefined, formFields: string[]) {
  if (!error) return undefined
  const shownBesideField = Object.keys(error.fields).some((name) => formFields.includes(name))
  return shownBesideField ? undefined : error.message
}
