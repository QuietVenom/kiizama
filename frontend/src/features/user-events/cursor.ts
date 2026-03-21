const USER_EVENTS_CURSOR_STORAGE_KEY = "user-events:last-event-id"
const USER_EVENTS_CURSOR_MAX_AGE_MS = 15 * 60 * 1000

type StoredUserEventsCursor = {
  updatedAt: number
  value: string
}

const isBrowser = () => typeof window !== "undefined"

const buildStorageKey = (userId: string) =>
  `${USER_EVENTS_CURSOR_STORAGE_KEY}:${userId}`

const parseStoredCursor = (
  rawValue: string | null,
): StoredUserEventsCursor | null => {
  if (!rawValue) {
    return null
  }

  try {
    const value = JSON.parse(rawValue) as Partial<StoredUserEventsCursor>
    if (
      typeof value.value !== "string" ||
      typeof value.updatedAt !== "number"
    ) {
      return null
    }
    return {
      value: value.value,
      updatedAt: value.updatedAt,
    }
  } catch {
    return null
  }
}

export const readUserEventsCursor = (userId: string): string | null => {
  if (!isBrowser()) {
    return null
  }

  const storageKey = buildStorageKey(userId)
  const storedValue = parseStoredCursor(
    window.sessionStorage.getItem(storageKey),
  )
  if (!storedValue) {
    window.sessionStorage.removeItem(storageKey)
    return null
  }

  if (Date.now() - storedValue.updatedAt > USER_EVENTS_CURSOR_MAX_AGE_MS) {
    window.sessionStorage.removeItem(storageKey)
    return null
  }

  return storedValue.value
}

export const writeUserEventsCursor = (userId: string, value: string): void => {
  if (!isBrowser()) {
    return
  }

  const storageKey = buildStorageKey(userId)
  const payload: StoredUserEventsCursor = {
    value,
    updatedAt: Date.now(),
  }
  window.sessionStorage.setItem(storageKey, JSON.stringify(payload))
}

export const clearUserEventsCursor = (userId: string): void => {
  if (!isBrowser()) {
    return
  }

  window.sessionStorage.removeItem(buildStorageKey(userId))
}
