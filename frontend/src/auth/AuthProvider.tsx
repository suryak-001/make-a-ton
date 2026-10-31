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

  return (
    <AuthContext.Provider
      value={{
        user: me.data ?? null,
        loading: me.isPending,
        login: (email, password) => loginMutation.mutateAsync({ email, password }),
        logout: async () => {
          await api.post('/auth/logout')
          qc.clear() // never keep another user's cached data around
          qc.setQueryData(['me'], null)
        },
      }}
    >
      {children}
    </AuthContext.Provider>
  )
}
