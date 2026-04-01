import { expect, type Page, type TestInfo, test } from "@playwright/test"
import { anonymousStorageState } from "./utils/storageState"

type VisualRoute = {
  path: string
  slug: string
}

const publicRoutes: VisualRoute[] = [
  { path: "/", slug: "landing" },
  { path: "/login", slug: "login" },
  { path: "/signup", slug: "signup" },
  { path: "/waiting-list", slug: "waiting-list" },
  { path: "/privacy", slug: "privacy" },
  { path: "/providers", slug: "providers" },
  { path: "/terms-conditions", slug: "terms-conditions" },
]

const privateRoutes: VisualRoute[] = [
  { path: "/overview", slug: "overview" },
  { path: "/settings", slug: "settings" },
]

const captureVisualState = async (
  page: Page,
  testInfo: TestInfo,
  route: VisualRoute,
  theme: "light" | "dark",
) => {
  await page.addInitScript((mode) => {
    window.localStorage.setItem("theme", mode)
  }, theme)

  await page.goto(route.path)
  await page.waitForLoadState("domcontentloaded")

  await expect
    .poll(async () =>
      page.evaluate(() => {
        if (document.documentElement.classList.contains("dark")) return "dark"
        if (document.documentElement.classList.contains("light")) return "light"
        return "unknown"
      }),
    )
    .toBe(theme)

  const screenshot = await page.screenshot({
    fullPage: true,
    animations: "disabled",
  })

  expect(screenshot.byteLength).toBeGreaterThan(0)

  await testInfo.attach(`${route.slug}-${theme}`, {
    body: screenshot,
    contentType: "image/png",
  })
}

test.describe("Public theme visuals", () => {
  test.use({
    storageState: anonymousStorageState,
    viewport: { width: 1440, height: 1100 },
  })

  test.beforeEach(async ({ page }) => {
    await page.route(
      "**/api/v1/public/feature-flags/waiting-list",
      async (route) => {
        await route.fulfill({
          status: 200,
          contentType: "application/json",
          body: JSON.stringify({
            key: "waiting-list",
            description: null,
            is_enabled: false,
            is_public: true,
          }),
        })
      },
    )
  })

  for (const theme of ["light", "dark"] as const) {
    for (const route of publicRoutes) {
      test(`captures ${route.path} in ${theme} mode`, async ({
        page,
      }, testInfo) => {
        await captureVisualState(page, testInfo, route, theme)
      })
    }
  }
})

test.describe("Authenticated theme visuals", () => {
  test.use({
    viewport: { width: 1440, height: 1100 },
  })

  for (const theme of ["light", "dark"] as const) {
    for (const route of privateRoutes) {
      test(`captures ${route.path} in ${theme} mode`, async ({
        page,
      }, testInfo) => {
        await captureVisualState(page, testInfo, route, theme)
      })
    }
  }
})
