import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import type { ReactNode } from 'react'
import { ApiError, api } from '@/lib/api'
import { AuthContext, type User } from './context'

async function fetchMe(): Promise<User | null> {
  try {
    return await api.get<User>('/auth/me')
  } catch (e) {
    if (e instanceof ApiError && e.status === 401) return null
    throw e
  }
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const qc = useQueryClient()
  const me = useQuery({ queryKey: ['me'], queryFn: fetchMe, staleTime: Infinity, retry: false })

  const loginMutation = useMutation({
    mutationFn: (v: { email: string; password: string }) => api.post<User>('/auth/login', v),
    onSuccess: (user) => qc.setQueryData(['me'], user),
  })

  const signupMutation = useMutation({
    mutationFn: (v: { name: string; email: string; password: string }) => api.post<User>('/auth/signup', v),
    onSuccess: (user) => qc.setQueryData(['me'], user),
  })

  return (
    <AuthContext.Provider
      value={{
        user: me.data ?? null,
        loading: me.isPending,
        login: (email, password) => loginMutation.mutateAsync({ email, password }),
        signup: (name, email, password) => signupMutation.mutateAsync({ name, email, password }),
        refresh: async () => { await qc.invalidateQueries({ queryKey: ['me'] }) },
        logout: async () => {
          await api.post('/auth/logout')
          qc.setQueryData(['me'], null)
          qc.removeQueries({ predicate: (query) => query.queryKey[0] !== 'me' }) // never keep another user's cached data around
        },
      }}
    >
      {children}
    </AuthContext.Provider>
  )
}
