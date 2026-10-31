import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { RouterProvider } from 'react-router'
import { AuthProvider } from '@/auth/AuthProvider'
import { ApiError } from '@/lib/api'
import { router } from '@/routes'
import './index.css'

// Don't retry errors that can't succeed on a second try (404 not found, 403, 409…): show them straight away.
const retry = (failures: number, error: Error) => !(error instanceof ApiError && error.status < 500) && failures < 2

const queryClient = new QueryClient({ defaultOptions: { queries: { refetchOnWindowFocus: false, retry } } })

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <QueryClientProvider client={queryClient}>
      <AuthProvider>
        <RouterProvider router={router} />
      </AuthProvider>
    </QueryClientProvider>
  </StrictMode>,
)
