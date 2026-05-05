export const INSTAGRAM_USERNAME_PATTERN =
  /^(?!.*\.\.)(?!\.)(?!.*\.$)[a-z0-9._]{1,30}$/
export const MAX_INSTAGRAM_USERNAMES = 50
const INSTAGRAM_PROFILE_HOSTS = new Set(["instagram.com", "www.instagram.com"])
const RESERVED_INSTAGRAM_PATHS = new Set([
  "accounts",
  "developer",
  "directory",
  "explore",
  "p",
  "reel",
  "reels",
  "stories",
  "tv",
])

const parseInstagramProfileUrl = (value: string) => {
  const trimmedValue = value.trim()
  if (!trimmedValue) {
    return null
  }

  const candidate = /^[a-z]+:\/\//i.test(trimmedValue)
    ? trimmedValue
    : trimmedValue.startsWith("instagram.com/") ||
        trimmedValue.startsWith("www.instagram.com/")
      ? `https://${trimmedValue}`
      : null

  if (!candidate) {
    return null
  }

  try {
    const parsedUrl = new URL(candidate)
    if (!INSTAGRAM_PROFILE_HOSTS.has(parsedUrl.hostname.toLowerCase())) {
      return null
    }

    const [firstSegment] = parsedUrl.pathname
      .split("/")
      .map((segment) => segment.trim())
      .filter(Boolean)

    if (!firstSegment) {
      return null
    }

    const normalizedSegment = firstSegment.toLowerCase()
    if (RESERVED_INSTAGRAM_PATHS.has(normalizedSegment)) {
      return null
    }

    return firstSegment
  } catch {
    return null
  }
}

export const normalizeInstagramUsername = (value: string) =>
  (
    parseInstagramProfileUrl(value) ?? value.trim().replace(/^@+/, "")
  ).toLowerCase()

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
