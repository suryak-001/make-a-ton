import { Route, Routes } from 'react-router'
import TemplateForm from './Form'
import TemplateList from './List'

export default function QuotationTemplatesPage() {
  return (
    <Routes>
      <Route index element={<TemplateList />} />
      <Route path="new" element={<TemplateForm />} />
      <Route path=":id" element={<TemplateForm />} />
    </Routes>
  )
}
