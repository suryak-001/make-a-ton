import { Download } from 'lucide-react'
import { qs } from '@/lib/api'
import { buttonClass } from './button-class'

/** Downloads every row the list's current filters match as CSV (the server applies the same filters). */
export function ExportLink({ path, params = {} }: { path: string; params?: Parameters<typeof qs>[0] }) {
  return (
    <a href={`/api${path}/export.csv${qs(params)}`} download className={buttonClass('outline', 'gap-1.5')}>
      <Download aria-hidden className="size-4" />
      Export CSV
    </a>
  )
}
