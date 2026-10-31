import { Route, Routes } from 'react-router'
import { RoutedModal } from '@/components/RoutedModal'
import DiscountForm from './Form'
import DiscountList from './List'

export default function DiscountsPage() {
  return (
    <>
      <DiscountList />
      <Routes>
        <Route path="new" element={<RoutedModal title="New discount" backTo="/discounts" wide><DiscountForm /></RoutedModal>} />
        <Route path=":id" element={<RoutedModal title="Edit discount" backTo="/discounts" wide><DiscountForm /></RoutedModal>} />
      </Routes>
    </>
  )
}
