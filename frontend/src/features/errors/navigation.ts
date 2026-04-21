import { clearStoredAccessToken } from "@/features/auth/session"

export const sanitizeReturnTo = (value: unknown) => {
  if (typeof value !== "string") {
    return undefined
  }

  const trimmedValue = value.trim()
  if (
    trimmedValue.length === 0 ||
    !trimmedValue.startsWith("/") ||
    trimmedValue.startsWith("//")
  ) {
    return undefined
  }

  return trimmedValue
}

export const getCurrentPathWithSearchAndHash = () => {
  if (typeof window === "undefined") {
    return undefined
  }

  return `${window.location.pathname}${window.location.search}${window.location.hash}`
}

export const buildLoginHrefWithReturnTo = (returnTo?: string) => {
  const safeReturnTo = sanitizeReturnTo(returnTo)

  if (
    !safeReturnTo ||
    safeReturnTo === "/login" ||
    safeReturnTo.startsWith("/login?")
  ) {
    return "/login"
  }

  return `/login?redirect=${encodeURIComponent(safeReturnTo)}`
}

export const getReturnToFromHref = (href: string) => {
  try {
    const url = new URL(href, "https://kiizama.com")
    return sanitizeReturnTo(url.searchParams.get("redirect"))
  } catch {
    return undefined
  }
}

export const redirectToLoginWithReturnTo = (returnTo?: string) => {
  clearStoredAccessToken()
  const loginHref = buildLoginHrefWithReturnTo(
    returnTo || getCurrentPathWithSearchAndHash(),
  )
  window.location.replace(loginHref)
}
