import { Navigate, Route, Routes } from 'react-router'
import { useAuth } from '@/auth/context'
import { RoutedModal } from '@/components/RoutedModal'
import PlanForm from './Form'
import PlanList from './List'

export default function PlansPage() {
  const { user } = useAuth()
  // Staff can open a plan to view it, but only an admin creates one.
  return (
    <>
      <PlanList />
      <Routes>
        <Route path="new" element={user?.role === 'ADMIN' ? <RoutedModal title="New plan" backTo="/plans" wide><PlanForm /></RoutedModal> : <Navigate to="/plans" replace />} />
        <Route path=":id" element={<RoutedModal title="Edit plan" backTo="/plans" wide><PlanForm /></RoutedModal>} />
      </Routes>
    </>
  )
}
