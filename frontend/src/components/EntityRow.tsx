import { useState } from 'react'
import { useNavigate } from 'react-router'
import { useRowMutations } from '@/lib/entity'
import { Alert } from './forms'
import { ConfirmDialog } from './ConfirmDialog'
import { RowActions } from './RowActions'
import { standardActions } from './row-actions'
import { StatusSelect } from './StatusSelect'

type Props = { path: string; id: number; name: string; active?: boolean; label: string }

/** Status dropdown for a list row: Active / Inactive, saved straight away. */
export function EntityStatus({ path, id, active, disabled }: { path: string; id: number; active: boolean; disabled?: boolean }) {
  const { setActive } = useRowMutations(path)
  return <StatusSelect active={active} disabled={disabled || setActive.isPending} onChange={(next) => setActive.mutate({ id, active: next })} />
}

/** The ⋯ menu for a list row (Edit, Mark active/inactive, Delete) with a confirm step that explains refusals. */
export function EntityRowMenu({ path, id, name, active, label }: Props) {
  const navigate = useNavigate()
  const { setActive, remove, error, clearError } = useRowMutations(path)
  const [asking, setAsking] = useState(false)

  const close = () => { setAsking(false); clearError() }
  // The dialog lives inside the clickable row, so keep its clicks and keys from reaching the row.
  return (
    <span onClick={(e) => e.stopPropagation()} onKeyDown={(e) => e.stopPropagation()}>
      <RowActions
        label={`Actions for ${name}`}
        actions={standardActions({
          active,
          onEdit: () => navigate(`${path}/${id}`),
          onToggle: active === undefined ? undefined : () => setActive.mutate({ id, active: !active }),
          onDelete: () => { clearError(); setAsking(true) },
        })}
      />
      <ConfirmDialog
        open={asking}
        onClose={close}
        onConfirm={() => remove.mutate(id, { onSuccess: close })}
        title={`Delete ${label}?`}
        confirmLabel="Delete"
        pending={remove.isPending}
      >
        <p>{name} will be removed for good.</p>
        {error && (
          <div className="mt-3 grid gap-2">
            <Alert>{error}</Alert>
            {active === true && <button type="button" className="justify-self-start text-[13px] font-medium text-brand underline underline-offset-4" onClick={() => setActive.mutate({ id, active: false }, { onSuccess: close })}>Mark it inactive instead</button>}
          </div>
        )}
      </ConfirmDialog>
    </span>
  )
}
