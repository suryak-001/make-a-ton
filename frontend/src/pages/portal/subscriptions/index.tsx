import { Route, Routes } from 'react-router'
import PortalSubscriptionDetail from './Detail'
import PortalSubscriptionList from './List'

export default function PortalSubscriptionsPage() {
  return (
    <Routes>
      <Route index element={<PortalSubscriptionList />} />
      <Route path=":id" element={<PortalSubscriptionDetail />} />
    </Routes>
  )
}
