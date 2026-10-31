import { Badge } from './ui'

export function ActiveBadge({ active }: { active: boolean }) {
  return active ? <Badge className="bg-green-50 text-green-800">Active</Badge> : <Badge className="bg-zinc-100 text-zinc-600">Inactive</Badge>
}
