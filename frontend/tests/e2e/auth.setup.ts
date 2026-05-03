import { expect, test as setup } from "@playwright/test"
import { firstSuperuser, firstSuperuserPassword } from "./config.ts"
import { ensureCookieConsent } from "./utils/storageState.ts"

const authFile = "playwright/.auth/user.json"

setup("authenticate", async ({ page }) => {
  await ensureCookieConsent(page)
  await page.goto("/login")
  await page.getByPlaceholder("Correo electrónico").fill(firstSuperuser)
  await page.getByPlaceholder("Contraseña").fill(firstSuperuserPassword)
  await page.getByRole("button", { name: "Iniciar sesión" }).click()
  await expect(page).toHaveURL(/\/overview$/)
  await page.context().storageState({ path: authFile })
})
