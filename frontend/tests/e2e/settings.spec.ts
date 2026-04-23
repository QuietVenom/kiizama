import { expect, type Page, test } from "@playwright/test"

import { createUser } from "./utils/privateApi.ts"
import { randomEmail, randomPassword } from "./utils/random"
import { anonymousStorageState } from "./utils/storageState.ts"
import { logInUser, logOutUser } from "./utils/user"

const themeStorageKey = "theme"

const openAppearanceTab = async (page: Page) => {
  await page.goto("/settings")
  await page.getByRole("tab", { name: "Appearance" }).click()
}

const clickAppearanceMode = async (
  page: Page,
  label: "System" | "Light Mode" | "Dark Mode",
) => {
  await page
    .locator("label")
    .filter({ hasText: label })
    .locator("span")
    .first()
    .click()
}

const getDocumentThemeClass = async (page: Page) => {
  return page.evaluate(() => {
    if (document.documentElement.classList.contains("dark")) return "dark"
    if (document.documentElement.classList.contains("light")) return "light"
    return "unknown"
  })
}

test.describe("settings profile persistence", () => {
  test.use({ storageState: anonymousStorageState })

  test("settings_profile_happy_path_persists_updated_information", async ({
    page,
  }) => {
    const email = randomEmail()
    const updatedEmail = randomEmail()
    const password = randomPassword()
    const updatedName = "Updated Settings User"

    await createUser({ email, password })
    await logInUser(page, email, password)

    await page.goto("/settings")
    await page.getByRole("button", { name: "Edit" }).click()
    await page.getByLabel("Full name").fill(updatedName)
    await page.getByLabel("Email").fill(updatedEmail)
    await page.getByRole("button", { name: "Save" }).click()

    await expect(page.getByText(/User updated successfully\.?/)).toBeVisible()
    await page.reload()
    await expect(
      page.getByLabel("My profile").getByText(updatedName, { exact: true }),
    ).toBeVisible()
    await expect(
      page.getByLabel("My profile").getByText(updatedEmail, { exact: true }),
    ).toBeVisible()
  })
})

test.describe("settings password persistence", () => {
  test.use({ storageState: anonymousStorageState })

  test("settings_password_happy_path_allows_login_with_new_password", async ({
    page,
  }) => {
    const email = randomEmail()
    const password = randomPassword()
    const newPassword = randomPassword()

    await createUser({ email, password })
    await logInUser(page, email, password)

    await page.goto("/settings")
    await page.getByRole("tab", { name: "Password" }).click()
    await page.getByPlaceholder("Current Password").fill(password)
    await page.getByPlaceholder("New Password").fill(newPassword)
    await page.getByPlaceholder("Confirm Password").fill(newPassword)
    await page.getByRole("button", { name: "Save" }).click()

    await expect(page.getByText("Password updated successfully.")).toBeVisible()
    await logOutUser(page)
    await logInUser(page, email, newPassword)
  })
})

test("settings_theme_system_mode_persists_and_follows_browser_preference", async ({
  page,
}) => {
  await page.emulateMedia({ colorScheme: "dark" })
  await openAppearanceTab(page)

  await clickAppearanceMode(page, "System")
  await expect.poll(async () => getDocumentThemeClass(page)).toBe("dark")
  await expect
    .poll(async () =>
      page.evaluate(
        (storageKey) => localStorage.getItem(storageKey),
        themeStorageKey,
      ),
    )
    .toBe("system")

  await page.reload()
  await expect.poll(async () => getDocumentThemeClass(page)).toBe("dark")

  await page.emulateMedia({ colorScheme: "light" })
  await expect.poll(async () => getDocumentThemeClass(page)).toBe("light")
})
