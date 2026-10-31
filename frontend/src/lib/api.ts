export class ApiError extends Error {
  status: number
  /** Per-field messages when the server tied the error to form fields (`{ email: "…" }`). */
  fields: Record<string, string>
  constructor(status: number, message: string, fields: Record<string, string> = {}) {
    super(message)
    this.status = status
    this.fields = fields
  }
}

type ValidationItem = { loc?: (string | number)[]; msg?: string; type?: string; ctx?: Record<string, unknown> }

/** Pydantic's built-in checks speak like a library ("String should have at least 1 character"); say it plainly.
 *  Messages the server wrote itself (value errors) are already meant for people and pass through. */
function friendly(item: ValidationItem): string {
  const ctx = item.ctx ?? {}
  switch (item.type) {
    case 'missing':
      return 'This field is required.'
    case 'string_too_short':
      return ctx.min_length === 1 ? 'This field is required.' : `Use at least ${ctx.min_length} characters.`
    case 'string_too_long':
      return `Use at most ${ctx.max_length} characters.`
    case 'greater_than':
      return `Must be more than ${ctx.gt}.`
    case 'greater_than_equal':
      return `Must be ${ctx.ge} or more.`
    case 'less_than':
      return `Must be less than ${ctx.lt}.`
    case 'less_than_equal':
      return `Must be ${ctx.le} or less.`
    case 'int_parsing':
    case 'int_type':
    case 'decimal_parsing':
    case 'decimal_type':
    case 'float_parsing':
      return 'Enter a number.'
    case 'date_parsing':
    case 'date_from_datetime_parsing':
    case 'date_type':
      return 'Enter a valid date.'
  }
  return (item.msg ?? 'Invalid value').replace(/^Value error, /, '')
}

function parseError(status: number, detail: unknown): ApiError {
  if (typeof detail === 'string') return new ApiError(status, detail)
  if (Array.isArray(detail)) {
    const fields: Record<string, string> = {}
    const messages: string[] = []
    for (const item of detail as ValidationItem[]) {
      const msg = friendly(item)
      const loc = (item.loc ?? []).filter((p) => p !== 'body')
      const key = loc.join('.')
      if (key && !(key in fields)) fields[key] = msg
      messages.push(key ? `${key}: ${msg}` : msg)
    }
    return new ApiError(status, messages[0] ?? 'Something went wrong', fields)
  }
  return new ApiError(status, 'Something went wrong')
}

async function request<T>(method: string, path: string, body?: unknown): Promise<T> {
  const res = await fetch(`/api${path}`, {
    method,
    headers: body === undefined ? undefined : { 'Content-Type': 'application/json' },
    body: body === undefined ? undefined : JSON.stringify(body),
    credentials: 'same-origin',
  })
  if (res.status === 204) return undefined as T
  const data = await res.json().catch(() => null)
  if (res.status === 401 && !path.startsWith('/auth/') && window.location.pathname !== '/login') {
    window.location.assign('/login') // the session ended (signed out elsewhere or expired): go sign in again
  }
  if (!res.ok) throw parseError(res.status, data?.detail)
  return data as T
}

export const api = {
  get: <T>(path: string) => request<T>('GET', path),
  post: <T>(path: string, body?: unknown) => request<T>('POST', path, body ?? {}),
  put: <T>(path: string, body: unknown) => request<T>('PUT', path, body),
  patch: <T>(path: string, body: unknown) => request<T>('PATCH', path, body),
  delete: <T>(path: string) => request<T>('DELETE', path),
}

export type Page<T> = { items: T[]; total: number; page: number; page_size: number }

/** `qs({ q: 'abc', page: 2, status: undefined })` -> `?q=abc&page=2` (empty values are dropped). */
export function qs(params: Record<string, string | number | boolean | null | undefined>) {
  const sp = new URLSearchParams()
  for (const [k, v] of Object.entries(params)) if (v !== undefined && v !== null && v !== '') sp.set(k, String(v))
  const s = sp.toString()
  return s ? `?${s}` : ''
}
