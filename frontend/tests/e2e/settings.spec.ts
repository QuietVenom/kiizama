import { expect, type Page, test } from "@playwright/test"

import { createUser } from "./utils/privateApi.ts"
import { randomEmail, randomPassword } from "./utils/random"
import { anonymousStorageState } from "./utils/storageState.ts"
import { logInUser, logOutUser } from "./utils/user"

const themeStorageKey = "theme"

const openAppearanceTab = async (page: Page) => {
  await page.goto("/settings")
  await page.getByRole("tab", { name: "Apariencia" }).click()
}

const clickAppearanceMode = async (
  page: Page,
  label: "Sistema" | "Modo claro" | "Modo oscuro",
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
    await page.getByRole("button", { name: "Editar" }).click()
    await page.getByLabel("Nombre completo").fill(updatedName)
    await page.getByLabel("Correo electrónico").fill(updatedEmail)
    await page.getByRole("button", { name: "Guardar" }).click()

    await expect(
      page.getByText(
        /La información del usuario se actualizó correctamente\.?/,
      ),
    ).toBeVisible()
    await page.reload()
    await expect(
      page.getByLabel("Mi perfil").getByText(updatedName, { exact: true }),
    ).toBeVisible()
    await expect(
      page.getByLabel("Mi perfil").getByText(updatedEmail, { exact: true }),
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
    await page.getByRole("tab", { name: "Contraseña" }).click()
    await page.getByPlaceholder("Contraseña actual").fill(password)
    await page.getByPlaceholder("Nueva contraseña").fill(newPassword)
    await page.getByPlaceholder("Confirmar contraseña").fill(newPassword)
    await page.getByRole("button", { name: "Guardar" }).click()

    await expect(
      page.getByText("La contraseña se actualizó correctamente."),
    ).toBeVisible()
    await logOutUser(page)
    await logInUser(page, email, newPassword)
  })
})

test("settings_theme_system_mode_persists_and_follows_browser_preference", async ({
  page,
}) => {
  await page.emulateMedia({ colorScheme: "dark" })
  await openAppearanceTab(page)

  await clickAppearanceMode(page, "Sistema")
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
