import type { ReactNode } from 'react'
import { Navigate } from 'react-router'
import { Forbidden } from '@/components/Forbidden'
import { type Role, useAuth } from './context'

/**
 * UX guard only — it decides what to render. The real authorization is the backend's
 * `require_roles(...)` on every route; never rely on this to protect data.
 */
export function RequireRole({ roles, children }: { roles: Role[]; children: ReactNode }) {
  const { user, loading } = useAuth()
  if (loading) return <p className="p-8 text-sm text-muted">Loading…</p>
  if (!user) return <Navigate to="/login" replace />
  if (user.must_change_password) return <Navigate to="/change-password" replace />
  if (!roles.includes(user.role)) return <Forbidden />
  return children
}
