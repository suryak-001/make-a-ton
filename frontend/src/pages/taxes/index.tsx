import { Route, Routes } from 'react-router'
import TaxForm from './Form'
import TaxList from './List'

export default function TaxesPage() {
  return (
    <Routes>
      <Route index element={<TaxList />} />
      <Route path="new" element={<TaxForm />} />
      <Route path=":id" element={<TaxForm />} />
    </Routes>
  )
}
