// Mirrors backend/app/core/security.py `password_problems`. The server is the authority; this only
// gives instant feedback while typing.
export const PASSWORD_RULES = [
  { label: 'More than 8 characters', test: (pw: string) => pw.length > 8 },
  { label: 'An uppercase letter', test: (pw: string) => /[A-Z]/.test(pw) },
  { label: 'A lowercase letter', test: (pw: string) => /[a-z]/.test(pw) },
  { label: 'A special character', test: (pw: string) => /[^A-Za-z0-9]/.test(pw) },
]

export const passwordIsValid = (pw: string) => PASSWORD_RULES.every((r) => r.test(pw))
