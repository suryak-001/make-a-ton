import { Navigate, Outlet } from 'react-router'
import { homeFor, useAuth } from '@/auth/context'
import { BrandMark } from './BrandMark'

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
    <main className="grid min-h-screen bg-surface lg:grid-cols-[minmax(0,1.15fr)_minmax(420px,.85fr)]">
      <section className="relative hidden overflow-hidden border-r border-ink bg-brand p-10 text-paper lg:flex lg:flex-col lg:justify-between">
        <BrandMark />
        <div className="relative z-10 max-w-xl">
          <p className="text-[10px] font-medium uppercase tracking-[0.25em] text-paper/70">Revenue operations / one clear loop</p>
          <h1 className="mt-5 text-[clamp(48px,6vw,88px)] font-medium leading-[0.88] tracking-[-0.065em]">Sell.<br />Bill.<br /><span className="text-yellow">Repeat.</span></h1>
          <p className="mt-7 max-w-sm text-[14px] leading-6 text-paper/75">Subscriptions, invoices and payments assembled into one precise operating system.</p>
        </div>
        <p className="relative z-10 text-[10px] uppercase tracking-[0.18em] text-paper/55">Built for recurring business</p>
        <div className="absolute -right-24 -top-24 size-80 rounded-full border-[48px] border-yellow" />
        <div className="absolute bottom-24 right-16 size-32 rotate-12 bg-danger" />
        <div className="absolute bottom-0 right-0 h-36 w-72 -skew-x-12 bg-ink" />
      </section>
      <section className="flex items-center justify-center p-6 sm:p-10">
        <div className="w-full max-w-sm">
          <div className="mb-8 lg:hidden"><BrandMark /></div>
          <Outlet />
          <p className="mt-6 text-center text-[10px] uppercase tracking-[0.16em] text-muted">Brightloop operating system</p>
        </div>
      </section>
    </main>
  )
}
