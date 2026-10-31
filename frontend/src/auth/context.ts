import { createContext, useContext } from 'react'

export type Role = 'ADMIN' | 'STAFF' | 'CUSTOMER'

export type User = {
  id: number
  email: string
  name: string
  role: Role
  customer_id: number | null // set for CUSTOMER users — portal queries are scoped by it server-side
}

export type AuthState = {
  user: User | null
  loading: boolean
  login: (email: string, password: string) => Promise<User>
  logout: () => Promise<void>
}

export const AuthContext = createContext<AuthState | null>(null)

export function useAuth() {
  const ctx = useContext(AuthContext)
  if (!ctx) throw new Error('useAuth must be used inside <AuthProvider>')
  return ctx
}

export const homeFor = (role: Role) => (role === 'CUSTOMER' ? '/portal/subscriptions' : '/dashboard')
