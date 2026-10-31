import { createContext, useContext } from 'react'

export type Role = 'ADMIN' | 'STAFF' | 'CUSTOMER'

export type User = {
  id: number
  email: string
  name: string
  role: Role
  customer_id: number | null // set for CUSTOMER users — portal queries are scoped by it server-side
  must_change_password?: boolean // staff an admin added: must pick their own password first
}

export type AuthState = {
  user: User | null
  loading: boolean
  login: (email: string, password: string) => Promise<User>
  signup: (name: string, email: string, password: string) => Promise<User>
  refresh: () => Promise<void>
  logout: () => Promise<void>
}

export const AuthContext = createContext<AuthState | null>(null)

export function useAuth() {
  const ctx = useContext(AuthContext)
  if (!ctx) throw new Error('useAuth must be used inside <AuthProvider>')
  return ctx
}

export const homeFor = (role: Role) => (role === 'CUSTOMER' ? '/portal/home' : '/dashboard')
