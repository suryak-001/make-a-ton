import { Route, Routes } from 'react-router'
import PortalInvoiceDetail from './Detail'
import PortalInvoiceList from './List'

export default function PortalInvoicesPage() { return <Routes><Route index element={<PortalInvoiceList />} /><Route path=":id" element={<PortalInvoiceDetail />} /></Routes> }
