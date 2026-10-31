import { Link } from 'react-router'
import { Placeholder } from '@/components/Placeholder'

type Props = { label: string; step: string; todo: string[] }

// Owner: A (A1/A2). Replace each of these with a real form.
export function AuthPlaceholder({ label, step, todo }: Props) {
  return (
    <div className="grid gap-4">
      <Placeholder item={{ label, owner: 'A', step, todo, href: '/' }} />
      <Link to="/login" className="text-center text-sm hover:underline">
        Back to sign in
      </Link>
    </div>
  )
}
