import type { NavItem } from '@/nav'
import { Badge, Card, PageHeader } from './ui'

/** Shown for any nav entry that has no page yet. Create src/pages/<route>/index.tsx to replace it. */
export function Placeholder({ item }: { item: Pick<NavItem, 'label' | 'owner' | 'step' | 'todo' | 'href'> }) {
  return (
    <>
      <PageHeader title={item.label} />
      <Card className="border-dashed p-5">
        <p className="flex items-center gap-2 font-medium">
          {item.label}
          <Badge>
            Person {item.owner} · {item.step}
          </Badge>
        </p>
        <p className="mt-1 text-sm text-muted">
          Not built yet — see PLAN.md step {item.step}. Create <code>src/pages{item.href}/index.tsx</code> (default export) to replace this.
        </p>
        <ul className="mt-3 list-disc space-y-1 pl-5 text-sm text-muted">
          {item.todo.map((t) => (
            <li key={t}>{t}</li>
          ))}
        </ul>
      </Card>
    </>
  )
}
