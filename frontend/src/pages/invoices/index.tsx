import { Route, Routes } from 'react-router'
import InvoiceDetail from './Detail'
import InvoiceList from './List'

export default function InvoicesPage() {
  return <Routes><Route index element={<InvoiceList />} /><Route path=":id" element={<InvoiceDetail />} /></Routes>
}
