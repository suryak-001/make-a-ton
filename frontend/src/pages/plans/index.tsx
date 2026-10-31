import { Route, Routes } from 'react-router'
import { RoutedModal } from '@/components/RoutedModal'
import PlanForm from './Form'
import PlanList from './List'

export default function PlansPage() {
  return (
    <>
      <PlanList />
      <Routes>
        <Route path="new" element={<RoutedModal title="New plan" backTo="/plans" wide><PlanForm /></RoutedModal>} />
        <Route path=":id" element={<RoutedModal title="Edit plan" backTo="/plans" wide><PlanForm /></RoutedModal>} />
      </Routes>
    </>
  )
}
