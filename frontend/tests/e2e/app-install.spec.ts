import { expect, test } from "@playwright/test"
import {
  expectBounded,
  expectNoPageOverflow,
  mockResponsiveSession,
} from "./utils/responsive"
import { ensureCookieConsent } from "./utils/storageState"

test("installation_launch_without_session_uses_existing_login_return_flow", async ({
  page,
  request,
}) => {
  await ensureCookieConsent(page)
  const response = await request.get("/manifest.webmanifest")
  const manifest = await response.json()
  await page.goto(manifest.start_url)
  await expect(page).toHaveURL(/\/login\?redirect=%2Foverview$/)
  await expect(page.locator('link[rel="manifest"]')).toHaveAttribute(
    "href",
    "/manifest.webmanifest",
  )
})

test("installation_metadata_and_assets_are_shared_across_application_routes", async ({
  page,
  request,
}) => {
  await mockResponsiveSession(page)
  await ensureCookieConsent(page)
  for (const route of [
    "/overview",
    "/settings?tab=installation",
    "/creators-search",
  ]) {
    await page.goto(route)
    await expect(page.locator('link[rel="manifest"]')).toHaveCount(1)
    await expect(page.locator('link[rel="manifest"]')).toHaveAttribute(
      "href",
      "/manifest.webmanifest",
    )
    await expect(page.locator('link[rel="apple-touch-icon"]')).toHaveAttribute(
      "sizes",
      "180x180",
    )
  }
  const response = await request.get("/manifest.webmanifest")
  expect(response.ok()).toBe(true)
  expect(response.headers()["content-type"]).toContain(
    "application/manifest+json",
  )
  const manifest = await response.json()
  expect(manifest).toMatchObject({
    id: "/",
    start_url: "/overview",
    scope: "/",
    display: "standalone",
  })
  for (const icon of manifest.icons) {
    const result = await request.get(icon.src)
    expect(result.ok()).toBe(true)
    expect(result.headers()["content-type"]).toContain("image/png")
    const data = await result.body()
    expect(`${data.readUInt32BE(16)}x${data.readUInt32BE(20)}`).toBe(icon.sizes)
  }
})

for (const language of ["es", "en", "pt-BR"]) {
  for (const admin of [false, true]) {
    test(`installation_settings_${language}_${admin ? "admin" : "user"}_guides_fit`, async ({
      page,
      context,
    }) => {
      await mockResponsiveSession(page, admin)
      await ensureCookieConsent(page)
      await context.addCookies([
        {
          name: "kiizama.language",
          value: language,
          domain: "localhost",
          path: "/",
        },
      ])
      await page.goto("/settings?tab=installation")
      const title = language === "en" ? "Install Kiizama" : "Instalar Kiizama"
      await expect(
        page.getByRole("tab", { name: title, exact: true }),
      ).toHaveAttribute("aria-selected", "true")
      await expect(
        page.getByRole("button", { name: title, exact: true }),
      ).toHaveCount(0)
      for (const width of [320, 440, 768, 1280]) {
        await page.setViewportSize({ width, height: 956 })
        for (const platform of ["iOS", "Android"]) {
          await page.getByRole("tab", { name: platform, exact: true }).click()
          const steps = page.getByRole("list", { name: new RegExp(platform) })
          await expect(steps.getByRole("listitem")).toHaveCount(4)
          await expectBounded(steps)
          await expectNoPageOverflow(page)
        }
      }
    })
  }
}

test("installation_prompt_survives_navigation_and_updates_only_on_browser_completion", async ({
  page,
}) => {
  await mockResponsiveSession(page)
  await ensureCookieConsent(page)
  await page.goto("/overview")
  await page.evaluate(() => {
    const event = new Event("beforeinstallprompt", { cancelable: true })
    Object.assign(event, {
      prompt: async () => {},
      userChoice: Promise.resolve({ outcome: "accepted" }),
    })
    window.dispatchEvent(event)
  })
  // Navigate through the client router; a full reload would discard the captured event.
  const menu = page.locator('header button[aria-haspopup="dialog"]')
  if (await menu.isVisible()) await menu.click()
  await page
    .getByRole("link", { name: /Settings|Configuración|Configurações/ })
    .first()
    .click()
  await page
    .getByRole("tab", { name: /Instal[alr].*Kiizama|Install Kiizama/ })
    .click()
  await page
    .getByRole("button", { name: /Instalar Kiizama|Install Kiizama/ })
    .click()
  await expect(page.getByRole("status")).toHaveText(
    /Request sent|Solicitud enviada|Solicitação enviada/,
  )
  await expect(page.getByRole("list")).toBeVisible()
  await page.evaluate(() => {
    window.dispatchEvent(new Event("appinstalled"))
  })
  await expect(page.getByRole("status")).toHaveText(
    /already installed|ya está instalada|já está instalado/,
  )
  await expect(page.getByRole("list")).toHaveCount(0)
})
