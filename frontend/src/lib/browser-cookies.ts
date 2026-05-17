export type BrowserCookieSameSite = "Lax" | "Strict" | "None"

export type BrowserCookieOptions = {
  domain?: string
  maxAge?: number
  path?: string
  sameSite?: BrowserCookieSameSite
  secure?: boolean
}

const DEFAULT_COOKIE_PATH = "/"
const DEFAULT_COOKIE_SAME_SITE: BrowserCookieSameSite = "Lax"

const getCurrentHostname = () => {
  if (typeof window === "undefined") {
    return null
  }

  return window.location.hostname.toLowerCase()
}

export const getCookieDomain = (hostname = getCurrentHostname()) => {
  if (!hostname) {
    return undefined
  }

  if (
    hostname === "staging.kiizama.com" ||
    hostname.endsWith(".staging.kiizama.com")
  ) {
    return ".staging.kiizama.com"
  }

  if (hostname === "kiizama.com" || hostname.endsWith(".kiizama.com")) {
    return ".kiizama.com"
  }

  return undefined
}

export const shouldUseSecureCookies = () => {
  if (typeof window === "undefined") {
    return false
  }

  return window.location.protocol === "https:"
}

export const readCookie = (name: string) => {
  if (typeof document === "undefined") {
    return null
  }

  const cookieValue = document.cookie
    .split("; ")
    .find((entry) => entry.startsWith(`${name}=`))

  if (!cookieValue) {
    return null
  }

  const rawValue = cookieValue.slice(name.length + 1)

  try {
    return decodeURIComponent(rawValue)
  } catch {
    return rawValue
  }
}

export const writeCookie = (
  name: string,
  value: string,
  options: BrowserCookieOptions = {},
) => {
  if (typeof document === "undefined") {
    return
  }

  const segments = [`${name}=${encodeURIComponent(value)}`]
  const {
    domain,
    maxAge,
    path = DEFAULT_COOKIE_PATH,
    sameSite = DEFAULT_COOKIE_SAME_SITE,
    secure = shouldUseSecureCookies(),
  } = options

  if (domain) {
    segments.push(`Domain=${domain}`)
  }

  if (path) {
    segments.push(`Path=${path}`)
  }

  if (typeof maxAge === "number") {
    segments.push(`Max-Age=${Math.floor(maxAge)}`)
  }

  if (secure) {
    segments.push("Secure")
  }

  segments.push(`SameSite=${sameSite}`)

  // biome-ignore lint/suspicious/noDocumentCookie: this shared utility intentionally manages first-party browser cookies.
  document.cookie = segments.join("; ")
}

export const deleteCookie = (
  name: string,
  options: Omit<BrowserCookieOptions, "maxAge"> = {},
) => {
  writeCookie(name, "", {
    ...options,
    maxAge: 0,
  })
}
