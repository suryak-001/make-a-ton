import { useMutation, useQueryClient } from '@tanstack/react-query'
import { type FormEvent, useState } from 'react'
import { DeleteButton } from '@/components/DeleteButton'
import { Alert, FormField, Input, Textarea } from '@/components/forms'
import { Button } from '@/components/ui'
import { api, ApiError } from '@/lib/api'
import type { Customer } from '@/lib/types'

/** Create or edit a customer. `onDeleted` runs after a delete (the detail page leaves for the list). */
export function CustomerForm({ customer, onDone, onDeleted = onDone }: { customer?: Customer; onDone: () => void; onDeleted?: () => void }) {
  const qc = useQueryClient()
  const [error, setError] = useState<ApiError>()

  const save = useMutation({
    mutationFn: (body: Record<string, string>) =>
      customer ? api.put<Customer>(`/customers/${customer.id}`, body) : api.post<Customer>('/customers', body),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['customers'] })
      qc.invalidateQueries({ queryKey: ['/customers'] })
      onDone()
    },
    onError: (e) => setError(e instanceof ApiError ? e : new ApiError(0, 'Could not save. Try again.')),
  })

  const remove = useMutation({
    mutationFn: () => api.delete(`/customers/${customer!.id}`),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['customers'] })
      onDeleted()
    },
    onError: (e) => setError(e instanceof ApiError ? e : new ApiError(0, 'Could not delete. Try again.')),
  })

  function onSubmit(e: FormEvent<HTMLFormElement>) {
    e.preventDefault()
    setError(undefined)
    save.mutate(Object.fromEntries(new FormData(e.currentTarget)) as Record<string, string>)
  }

  const fields = error?.fields ?? {}
  return (
    <form onSubmit={onSubmit} className="grid gap-4" noValidate>
      <FormField label="Name" htmlFor="name" error={fields.name}>
        <Input id="name" name="name" defaultValue={customer?.name} required error={!!fields.name} />
      </FormField>
      <FormField label="Email" htmlFor="email" error={fields.email}>
        <Input id="email" name="email" type="email" defaultValue={customer?.email} required error={!!fields.email} />
      </FormField>
      <FormField label="Phone" htmlFor="phone" error={fields.phone}>
        <Input id="phone" name="phone" defaultValue={customer?.phone ?? ''} />
      </FormField>
      <FormField label="Address" htmlFor="address" error={fields.address}>
        <Textarea id="address" name="address" defaultValue={customer?.address ?? ''} />
      </FormField>
      {error && Object.keys(fields).length === 0 && <Alert>{error.message}</Alert>}
      <div className="flex items-center justify-between gap-2">
        <div>
          {customer && (
            <DeleteButton label="Delete customer" name={customer.name} pending={remove.isPending} onConfirm={() => remove.mutate()} />
          )}
        </div>
        <div className="flex gap-2">
          <Button type="button" variant="outline" onClick={onDone}>
            Cancel
          </Button>
          <Button type="submit" disabled={save.isPending}>
            {save.isPending ? 'Saving…' : 'Save'}
          </Button>
        </div>
      </div>
    </form>
  )
}
