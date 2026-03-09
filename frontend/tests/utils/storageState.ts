import type { BrowserContext, Page } from "@playwright/test"

const oneYearInSeconds = 60 * 60 * 24 * 365

const cookieConsentPreferences = encodeURIComponent(
  JSON.stringify({
    strictlyNecessary: true,
    functional: true,
    analytics: true,
    marketing: true,
  }),
)

const cookieConsentCookie = {
  name: "notion_cookie_consent",
  value: cookieConsentPreferences,
  domain: "localhost",
  path: "/",
  expires: Math.floor(Date.now() / 1000) + oneYearInSeconds,
  httpOnly: false,
  secure: false,
  sameSite: "Lax" as const,
}

export const anonymousStorageState = {
  cookies: [cookieConsentCookie],
  origins: [],
}

export async function ensureCookieConsent(
  pageOrContext: Page | BrowserContext,
) {
  const context =
    "context" in pageOrContext ? pageOrContext.context() : pageOrContext

  await context.addCookies([cookieConsentCookie])
}
