import { expect, type Page } from "@playwright/test"
import { ensureCookieConsent } from "./storageState.ts"

export async function signUpNewUser(
  page: Page,
  name: string,
  email: string,
  password: string,
) {
  await ensureCookieConsent(page)
  await page.goto("/signup")

  await page.getByPlaceholder("Full Name").fill(name)
  await page.getByPlaceholder("Email").fill(email)
  await page.getByPlaceholder("Password", { exact: true }).fill(password)
  await page.getByPlaceholder("Confirm Password").fill(password)
  await page.getByRole("button", { name: "Sign Up" }).click()
  await page.getByTestId("accept-privacy-checkbox").click()
  await page.getByTestId("accept-terms-checkbox").click()
  await page.getByTestId("confirm-legal-acceptance").click()
  await page.goto("/login")
}

export async function logInUser(page: Page, email: string, password: string) {
  await ensureCookieConsent(page)
  await page.goto("/login")

  await page.getByPlaceholder("Email").fill(email)
  await page.getByPlaceholder("Password", { exact: true }).fill(password)
  await page.getByRole("button", { name: "Log In" }).click()
  await expect(page).toHaveURL(/\/overview$/)
  await expect(
    page.getByText("Welcome back, nice to see you again!"),
  ).toBeVisible()
}

export async function logOutUser(page: Page) {
  const legacyUserMenu = page.getByTestId("user-menu")
  if ((await legacyUserMenu.count()) > 0) {
    await legacyUserMenu.click()
    await page.getByRole("menuitem", { name: /^log out$/i }).click()
    await expect(page).toHaveURL(/\/login$/)
    return
  }

  const sidebarLogoutButton = page
    .getByRole("button", { name: /^log out$/i })
    .first()
  const hasVisibleSidebarLogout = await sidebarLogoutButton
    .waitFor({ state: "visible", timeout: 1500 })
    .then(() => true)
    .catch(() => false)

  if (hasVisibleSidebarLogout) {
    await sidebarLogoutButton.click()
    await expect(page).toHaveURL(/\/login$/)
    return
  }

  await page.getByRole("button", { name: /open menu/i }).click()
  await page
    .getByRole("button", { name: /^log out$/i })
    .first()
    .click()
  await expect(page).toHaveURL(/\/login$/)
}
