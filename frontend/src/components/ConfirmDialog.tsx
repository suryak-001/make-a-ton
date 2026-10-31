import { type ReactNode } from 'react'
import { Modal } from './Modal'
import { Button } from './ui'

export function ConfirmDialog({ open, onClose, onConfirm, title, children, confirmLabel = 'Confirm', pending = false, tone = 'danger' }: { open: boolean; onClose: () => void; onConfirm: () => void; title: string; children: ReactNode; confirmLabel?: string; pending?: boolean; tone?: 'danger' | 'default' }) {
  return (
    <Modal open={open} onClose={onClose} title={title} status="Confirmation">
      <div className="grid gap-5">
        <div className="text-[13px] leading-5 text-muted">{children}</div>
        <div className="grid grid-cols-2 gap-2 border-t border-line pt-4">
          <Button type="button" variant="outline" onClick={onClose}>Cancel</Button>
          <Button type="button" disabled={pending} onClick={onConfirm} className={tone === 'danger' ? 'border-danger bg-danger text-white' : ''}>{pending ? 'Working…' : confirmLabel}</Button>
        </div>
      </div>
    </Modal>
  )
}
