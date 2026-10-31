import { Pencil, Power, Trash2 } from 'lucide-react'
import type { RowAction } from './RowActions'

/** Edit / Active-Inactive / Delete in one go, so every list builds its menu the same way. */
export function standardActions({ active, onEdit, onToggle, onDelete }: { active?: boolean; onEdit: () => void; onToggle?: () => void; onDelete?: () => void }): RowAction[] {
  return [
    { label: 'Edit', icon: Pencil, onSelect: onEdit },
    ...(onToggle ? [{ label: active ? 'Mark inactive' : 'Mark active', icon: Power, onSelect: onToggle }] : []),
    ...(onDelete ? [{ label: 'Delete', icon: Trash2, onSelect: onDelete, danger: true }] : []),
  ]
}
