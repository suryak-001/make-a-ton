import { Route, Routes } from 'react-router'
import PlanForm from './Form'
import PlanList from './List'

export default function PlansPage() {
  return (
    <Routes>
      <Route index element={<PlanList />} />
      <Route path="new" element={<PlanForm />} />
      <Route path=":id" element={<PlanForm />} />
    </Routes>
  )
}
