import { Link } from 'react-router'
import { Button } from './ui'

/** Cancel / Save, plus an optional Delete on the left for an existing record. */
export function FormActions({ cancelTo, saving, saveLabel, onDelete, deleteLabel }: { cancelTo: string; saving: boolean; saveLabel: string; onDelete?: () => void; deleteLabel?: string }) {
  return (
    <div className="flex items-center justify-between">
      <div>
        {onDelete && (
          <Button type="button" variant="ghost" className="text-danger" onClick={onDelete}>
            {deleteLabel}
          </Button>
        )}
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
