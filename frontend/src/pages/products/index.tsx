import { Route, Routes } from 'react-router'
import ProductForm from './Form'
import ProductList from './List'

export default function ProductsPage() {
  return (
    <Routes>
      <Route index element={<ProductList />} />
      <Route path="new" element={<ProductForm />} />
      <Route path=":id" element={<ProductForm />} />
    </Routes>
  )
}
