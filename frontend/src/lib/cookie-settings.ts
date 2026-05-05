import { getCookieDomain, shouldUseSecureCookies } from "./browser-cookies"

export const COOKIE_MAX_AGE_ONE_YEAR_SECONDS = 60 * 60 * 24 * 365
export const COOKIE_MAX_AGE_ONE_YEAR_MINUTES =
  COOKIE_MAX_AGE_ONE_YEAR_SECONDS / 60
export const COOKIE_CONSENT_NAME = "kiizama_cookie_consent"
export const LEGACY_COOKIE_CONSENT_NAME = "notion_cookie_consent"

export const getSharedCookieOptions = () => ({
  domain: getCookieDomain(),
  maxAge: COOKIE_MAX_AGE_ONE_YEAR_SECONDS,
  path: "/",
  sameSite: "Lax" as const,
  secure: shouldUseSecureCookies(),
})
