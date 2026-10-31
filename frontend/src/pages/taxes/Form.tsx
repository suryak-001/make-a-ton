import { type FormEvent, useState } from 'react'
import { useNavigate, useParams } from 'react-router'
import { Link } from 'react-router'
import { Alert, Checkbox, FormField, Input, Select } from '@/components/forms'
import { FormActions } from '@/components/FormActions'
import { WithEntity } from '@/components/WithEntity'
import { Card, PageHeader } from '@/components/ui'
import { generalMessage, useEntityMutations } from '@/lib/entity'
import type { TaxRule } from '@/lib/types'

type Draft = { name: string; kind: TaxRule['kind']; rate: string; active: boolean }

const EMPTY: Draft = { name: '', kind: 'PERCENT', rate: '', active: true }
const FIELDS = ['name', 'kind', 'rate']

export default function TaxFormPage() {
  const { id } = useParams()
  return (
    <WithEntity<TaxRule> id={id} path="/taxes" label="tax">
      {(tax) => <TaxEditor key={id ?? 'new'} tax={tax} />}
    </WithEntity>
  )
}

function TaxEditor({ tax }: { tax?: TaxRule }) {
  const navigate = useNavigate()
  const [draft, setDraft] = useState<Draft>(tax ?? EMPTY)
  const { save, remove, error, clearError } = useEntityMutations('/taxes', () => navigate('/taxes'))
  const set = <K extends keyof Draft>(key: K, value: Draft[K]) => setDraft((d) => ({ ...d, [key]: value }))

  function onSubmit(e: FormEvent) {
    e.preventDefault()
    clearError()
    save.mutate({ id: tax?.id, body: { name: draft.name, kind: draft.kind, rate: draft.rate || '0', active: draft.active } })
  }
  const askToDelete = () => remove.mutate(tax!.id)

  const fields = error?.fields ?? {}
  const message = generalMessage(error, FIELDS)
  const isPercent = draft.kind === 'PERCENT'

  return (
    <>
      <PageHeader title={tax ? tax.name : 'New tax'} actions={<Link to="/taxes" className="text-sm text-muted hover:underline">← All taxes</Link>} />
      <form onSubmit={onSubmit} noValidate className="grid max-w-xl gap-6">
        <Card className="grid gap-4 p-5 sm:grid-cols-2">
          <FormField label="Name" htmlFor="name" error={fields.name} className="sm:col-span-2">
            <Input id="name" value={draft.name} onChange={(e) => set('name', e.target.value)} required error={!!fields.name} />
          </FormField>
          <FormField label="Type" htmlFor="kind" error={fields.kind}>
            <Select id="kind" value={draft.kind} onChange={(e) => set('kind', e.target.value as Draft['kind'])}>
              <option value="PERCENT">Percentage of the line</option>
              <option value="FIXED">Fixed amount per unit</option>
            </Select>
          </FormField>
          <FormField label={isPercent ? 'Rate (%)' : 'Amount per unit'} htmlFor="rate" error={fields.rate}>
            <Input id="rate" inputMode="decimal" value={draft.rate} onChange={(e) => set('rate', e.target.value)} required error={!!fields.rate} />
          </FormField>
          <Checkbox label="Active" hint="Inactive taxes stop applying to new and re-saved quotes. Existing lines keep their amounts." checked={draft.active} onChange={(e) => set('active', e.target.checked)} />
        </Card>
        {message && <Alert>{message}</Alert>}
        <FormActions cancelTo="/taxes" saving={save.isPending} saveLabel="Save tax" onDelete={tax && askToDelete} deleteLabel="Delete tax" deleteName={tax?.name} />
      </form>
    </>
  )
}
