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
  confirm,
  onConfirm,
}: {
  id: string
  name?: string
  label?: string
  value: string
  onChange: (value: string) => void
  error?: string
  autoComplete?: string
  /** Pass both to add a "Re-enter password" box that must match. */
  confirm?: string
  onConfirm?: (value: string) => void
}) {
  const mismatch = confirm !== undefined && confirm.length > 0 && confirm !== value
  return (
    <>
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
    {confirm !== undefined && onConfirm && (
      <FormField label="Re-enter password" htmlFor={`${id}-confirm`} error={mismatch ? 'The two passwords don’t match.' : undefined}>
        <Input id={`${id}-confirm`} type="password" autoComplete={autoComplete} value={confirm} onChange={(e) => onConfirm(e.target.value)} required error={mismatch} />
      </FormField>
    )}
    </>
  )
}
