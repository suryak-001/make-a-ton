import type { ComponentType } from 'react'
import { Navigate, createBrowserRouter } from 'react-router'
import { RequireRole } from '@/auth/RequireRole'
import { AppShell } from '@/components/AppShell'
import { Forbidden } from '@/components/Forbidden'
import { Home, PublicOnly } from '@/components/RouteLayouts'
import { Placeholder } from '@/components/Placeholder'
import { APP_NAV, PORTAL_NAV, type NavItem } from '@/nav'
import ForgotPassword from '@/pages/auth/ForgotPassword'
import ResetPassword from '@/pages/auth/ResetPassword'
import Signup from '@/pages/auth/Signup'
import Login from '@/pages/Login'

/**
 * Real pages register themselves: create src/pages/<route>/index.tsx with a default export
 * (e.g. src/pages/subscriptions/index.tsx -> /subscriptions, src/pages/portal/invoices/index.tsx ->
 * /portal/invoices) and it replaces the placeholder. No edits to this file needed. A page that needs
 * sub-pages (/new, /:id) renders its own <Routes> — see src/pages/subscriptions for an example.
 */
const modules = import.meta.glob<{ default: ComponentType }>('./pages/**/index.tsx', { eager: true })
const pageFor = (href: string) => modules[`./pages${href}/index.tsx`]?.default

function routeFor(item: NavItem) {
  const Page = pageFor(item.href)
  return {
    path: `${item.href}/*`, // trailing /* lets a page render its own sub-routes (new, :id, …)
    element: <RequireRole roles={item.roles}>{Page ? <Page /> : <Placeholder item={item} />}</RequireRole>,
  }
}

export const router = createBrowserRouter([
  { path: '/', element: <Home /> },
  {
    element: <PublicOnly />,
    children: [
      { path: '/login', element: <Login /> },
      { path: '/signup', element: <Signup /> },
      { path: '/forgot-password', element: <ForgotPassword /> },
      { path: '/reset-password', element: <ResetPassword /> },
    ],
  },
  {
    element: (
      <RequireRole roles={['ADMIN', 'STAFF']}>
        <AppShell nav={APP_NAV} />
      </RequireRole>
    ),
    children: APP_NAV.map(routeFor),
  },
  {
    element: (
      <RequireRole roles={['CUSTOMER']}>
        <AppShell nav={PORTAL_NAV} />
      </RequireRole>
    ),
    children: [{ path: '/portal', element: <Navigate to="/portal/subscriptions" replace /> }, ...PORTAL_NAV.map(routeFor)],
  },
  { path: '*', element: <Forbidden /> },
])
