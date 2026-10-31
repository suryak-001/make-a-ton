import { Link } from 'react-router'
import { DeleteButton } from './DeleteButton'
import { Button } from './ui'

/** Cancel / Save, plus an optional Delete on the left for an existing record. */
export function FormActions({ cancelTo, saving, saveLabel, onDelete, deleteLabel, deleteName }: { cancelTo: string; saving: boolean; saveLabel: string; onDelete?: () => void; deleteLabel?: string; deleteName?: string }) {
  return (
    <div className="flex items-center justify-between">
      <div>
        {onDelete && <DeleteButton label={deleteLabel ?? 'Delete'} name={deleteName ?? 'This record'} onConfirm={onDelete} />}
      </div>
      <div className="flex gap-2">
        <Link to={cancelTo} className="inline-flex h-9 items-center rounded-md border border-line px-3 text-sm hover:bg-surface">
          Cancel
        </Link>
        <Button type="submit" disabled={saving}>
          {saving ? 'Saving…' : saveLabel}
        </Button>
      </div>
    </div>
  )
}
