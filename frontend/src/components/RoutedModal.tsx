import type { ReactNode } from 'react'
import { useNavigate } from 'react-router'
import { InModalContext } from './modal-context'
import { Modal } from './Modal'

/** A form shown as a pop-up over its list: the URL still says /taxes/new or /taxes/3, closing goes back to the list. */
export function RoutedModal({ title, backTo, wide, children }: { title: string; backTo: string; wide?: boolean; children: ReactNode }) {
  const navigate = useNavigate()
  return (
    <Modal open onClose={() => navigate(backTo)} title={title} wide={wide}>
      <InModalContext.Provider value>{children}</InModalContext.Provider>
    </Modal>
  )
}
