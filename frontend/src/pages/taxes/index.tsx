import { Route, Routes } from 'react-router'
import { RoutedModal } from '@/components/RoutedModal'
import TaxForm from './Form'
import TaxList from './List'

export default function TaxesPage() {
  return (
    <>
      <TaxList />
      <Routes>
        <Route path="new" element={<RoutedModal title="New tax" backTo="/taxes"><TaxForm /></RoutedModal>} />
        <Route path=":id" element={<RoutedModal title="Edit tax" backTo="/taxes"><TaxForm /></RoutedModal>} />
      </Routes>
    </>
  )
}
