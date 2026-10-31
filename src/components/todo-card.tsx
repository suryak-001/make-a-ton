import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";

/** Placeholder shown until the owner replaces the page. Delete once the feature lands. */
export function TodoCard({ title, owner, step, todo }: { title: string; owner: "A" | "B"; step: string; todo: string[] }) {
  return (
    <Card className="border-dashed">
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          {title}
          <Badge variant="outline">
            Person {owner} · {step}
          </Badge>
        </CardTitle>
        <CardDescription>Not built yet — see PLAN.md step {step}.</CardDescription>
      </CardHeader>
      <CardContent>
        <ul className="list-disc space-y-1 pl-5 text-sm text-muted-foreground">
          {todo.map((t) => (
            <li key={t}>{t}</li>
          ))}
        </ul>
      </CardContent>
    </Card>
  );
}
