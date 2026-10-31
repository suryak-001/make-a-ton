import { Route, Routes } from 'react-router'
import DiscountForm from './Form'
import DiscountList from './List'

export default function DiscountsPage() {
  return (
    <Routes>
      <Route index element={<DiscountList />} />
      <Route path="new" element={<DiscountForm />} />
      <Route path=":id" element={<DiscountForm />} />
    </Routes>
  )
}
