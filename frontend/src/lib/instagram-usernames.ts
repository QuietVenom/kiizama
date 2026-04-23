export const INSTAGRAM_USERNAME_PATTERN =
  /^(?!.*\.\.)(?!\.)(?!.*\.$)[a-z0-9._]{1,30}$/
export const MAX_INSTAGRAM_USERNAMES = 50

export const normalizeInstagramUsername = (value: string) =>
  value.trim().replace(/^@+/, "").toLowerCase()

export const sanitizeInstagramUsernames = (value: string[]) =>
  Array.from(
    new Set(
      value.map((item) => normalizeInstagramUsername(item)).filter(Boolean),
    ),
  )

export const isValidInstagramUsername = (value: string) =>
  INSTAGRAM_USERNAME_PATTERN.test(value)

export const areStringArraysEqual = (left: string[], right: string[]) =>
  left.length === right.length &&
  left.every((value, index) => value === right[index])

export const parseInstagramUsernamesInput = (
  input: string,
  max = MAX_INSTAGRAM_USERNAMES,
) => sanitizeInstagramUsernames(input.split(/[\s,]+/)).slice(0, max)
