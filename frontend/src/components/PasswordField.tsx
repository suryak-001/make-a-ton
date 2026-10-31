import clsx from 'clsx'
import { PASSWORD_RULES } from '@/lib/password'
import { FormField, Input } from './forms'

/** Password input with a live checklist of the policy (the server enforces it too). */
export function PasswordField({
  id,
  name = 'password',
  label = 'Password',
  value,
  onChange,
  error,
  autoComplete = 'new-password',
}: {
  id: string
  name?: string
  label?: string
  value: string
  onChange: (value: string) => void
  error?: string
  autoComplete?: string
}) {
  return (
    <FormField label={label} htmlFor={id} error={error}>
      <Input
        id={id}
        name={name}
        type="password"
        autoComplete={autoComplete}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        aria-describedby={`${id}-rules`}
        required
        error={!!error}
      />
      <ul id={`${id}-rules`} className="grid gap-0.5 text-xs">
        {PASSWORD_RULES.map((rule) => {
          const ok = rule.test(value)
          return (
            <li key={rule.label} className={clsx('flex items-center gap-1.5', ok ? 'text-green-700' : 'text-muted')}>
              <span aria-hidden>{ok ? '✓' : '○'}</span>
              {rule.label}
              <span className="sr-only">{ok ? '(met)' : '(not met yet)'}</span>
            </li>
          )
        })}
      </ul>
    </FormField>
  )
}
