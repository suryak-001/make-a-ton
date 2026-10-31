import { Navigate, Route, Routes } from 'react-router'
import { useAuth } from '@/auth/context'
import { RoutedModal } from '@/components/RoutedModal'
import ProductForm from './Form'
import ProductList from './List'

export default function ProductsPage() {
  const { user } = useAuth()
  // Staff can open a product to view it, but only an admin creates one.
  return (
    <>
      <ProductList />
      <Routes>
        <Route path="new" element={user?.role === 'ADMIN' ? <RoutedModal title="New product" backTo="/products" wide><ProductForm /></RoutedModal> : <Navigate to="/products" replace />} />
        <Route path=":id" element={<RoutedModal title="Edit product" backTo="/products" wide><ProductForm /></RoutedModal>} />
      </Routes>
    </>
  )
}
