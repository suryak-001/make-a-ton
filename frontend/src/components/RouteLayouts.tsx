import { Navigate, Outlet } from 'react-router'
import { homeFor, useAuth } from '@/auth/context'

export function Home() {
  const { user, loading } = useAuth()
  if (loading) return null
  return <Navigate to={user ? homeFor(user.role) : '/login'} replace />
}

export function PublicOnly() {
  const { user, loading } = useAuth()
  if (loading) return null
  if (user) return <Navigate to={homeFor(user.role)} replace />
  return (
    <main className="flex min-h-screen items-center justify-center bg-surface p-6">
      <div className="w-full max-w-sm">
        <p className="mb-6 text-center text-lg font-semibold tracking-tight">Brightloop</p>
        <Outlet />
      </div>
    </main>
  )
}
