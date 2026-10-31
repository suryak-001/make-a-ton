import { Route, Routes } from 'react-router'
import SubscriptionDetail from './Detail'
import SubscriptionForm from './Form'
import SubscriptionList from './List'

export default function SubscriptionsPage() {
  return (
    <Routes>
      <Route index element={<SubscriptionList />} />
      <Route path="new" element={<SubscriptionForm />} />
      <Route path=":id" element={<SubscriptionDetail />} />
      <Route path=":id/edit" element={<SubscriptionForm />} />
    </Routes>
  )
}
