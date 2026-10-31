import { Route, Routes } from 'react-router'
import CustomerDetail from './Detail'
import CustomerList from './List'

export default function CustomersPage() {
  return (
    <Routes>
      <Route index element={<CustomerList />} />
      <Route path=":id" element={<CustomerDetail />} />
    </Routes>
  )
}
