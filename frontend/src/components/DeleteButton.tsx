import { Trash2 } from 'lucide-react'
import { useState } from 'react'
import { ConfirmDialog } from './ConfirmDialog'
import { Button } from './ui'

/** "Delete …" with the same confirm pop-up everywhere (never the browser's own confirm box). */
export function DeleteButton({ label, name, pending, onConfirm }: { label: string; name: string; pending?: boolean; onConfirm: () => void }) {
  const [asking, setAsking] = useState(false)
  return (
    <>
      <Button type="button" variant="ghost" className="gap-1.5 text-danger" disabled={pending} onClick={() => setAsking(true)}>
        <Trash2 className="size-4" /> {label}
      </Button>
      <ConfirmDialog open={asking} onClose={() => setAsking(false)} onConfirm={() => { setAsking(false); onConfirm() }} title={`${label}?`} confirmLabel="Delete" pending={pending}>
        <p>{name} will be removed for good.</p>
      </ConfirmDialog>
    </>
  )
}
