import { Route, Routes } from 'react-router'
import { RoutedModal } from '@/components/RoutedModal'
import ProductForm from './Form'
import ProductList from './List'

export default function ProductsPage() {
  return (
    <>
      <ProductList />
      <Routes>
        <Route path="new" element={<RoutedModal title="New product" backTo="/products" wide><ProductForm /></RoutedModal>} />
        <Route path=":id" element={<RoutedModal title="Edit product" backTo="/products" wide><ProductForm /></RoutedModal>} />
      </Routes>
    </>
  )
}
