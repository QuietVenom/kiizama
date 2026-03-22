import type { BrowserContext, Page } from "@playwright/test"

const oneYearInSeconds = 60 * 60 * 24 * 365
const cookieConsentHosts = ["localhost", "127.0.0.1"]

const cookieConsentPreferences = encodeURIComponent(
  JSON.stringify({
    strictlyNecessary: true,
    functional: true,
    analytics: true,
    marketing: true,
  }),
)

const cookieConsentCookies = cookieConsentHosts.map((domain) => ({
  name: "notion_cookie_consent",
  value: cookieConsentPreferences,
  domain,
  path: "/",
  expires: Math.floor(Date.now() / 1000) + oneYearInSeconds,
  httpOnly: false,
  secure: false,
  sameSite: "Lax" as const,
}))

export const anonymousStorageState = {
  cookies: cookieConsentCookies,
  origins: [],
}

export async function ensureCookieConsent(
  pageOrContext: Page | BrowserContext,
) {
  const context =
    "context" in pageOrContext ? pageOrContext.context() : pageOrContext

  await context.addCookies(cookieConsentCookies)
}
