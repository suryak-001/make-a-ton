import { Route, Routes, useParams } from 'react-router'
import { RoutedModal } from '@/components/RoutedModal'
import SubscriptionDetail from './Detail'
import SubscriptionForm from './Form'
import SubscriptionList from './List'

/** New subscription pops up over the list; Edit pops up over the subscription being edited. */
function NewOverList() {
  return (
    <>
      <SubscriptionList />
      <RoutedModal title="New subscription" backTo="/subscriptions" wide><SubscriptionForm /></RoutedModal>
    </>
  )
}

function EditOverDetail() {
  const { id } = useParams()
  return (
    <>
      <SubscriptionDetail />
      <RoutedModal title="Edit subscription" backTo={`/subscriptions/${id}`} wide><SubscriptionForm /></RoutedModal>
    </>
  )
}

export default function SubscriptionsPage() {
  return (
    <Routes>
      <Route index element={<SubscriptionList />} />
      <Route path="new" element={<NewOverList />} />
      <Route path=":id" element={<SubscriptionDetail />} />
      <Route path=":id/edit" element={<EditOverDetail />} />
    </Routes>
  )
}
