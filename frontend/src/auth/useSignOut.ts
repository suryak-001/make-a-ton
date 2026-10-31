import { useAuth } from './context'

/** Signs out and lands on the sign-in page with a clean slate (a full reload, so nothing of the old session lingers). */
export function useSignOut() {
  const { logout } = useAuth()
  return async () => {
    try {
      await logout()
    } finally {
      window.location.assign('/login')
    }
  }
}
