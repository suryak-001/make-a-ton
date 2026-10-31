import { Link } from 'react-router'

export function Forbidden() {
  return (
    <div className="flex flex-1 flex-col items-center justify-center gap-3 p-8 text-center">
      <p className="text-sm font-medium text-muted">403</p>
      <h1 className="text-2xl font-semibold">You don&apos;t have access to this page</h1>
      <p className="text-muted">Ask an admin if you think you should.</p>
      <Link to="/" className="inline-flex h-9 items-center rounded-md border border-line px-3 text-sm hover:bg-surface">
        Go home
      </Link>
    </div>
  )
}
