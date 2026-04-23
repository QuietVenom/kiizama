import { expect, test } from "@playwright/test"

import { firstSuperuser, firstSuperuserPassword } from "./config.ts"
import { getPasswordRecoveryLink } from "./utils/passwordRecovery.ts"
import { randomEmail, randomPassword } from "./utils/random.ts"
import { anonymousStorageState } from "./utils/storageState.ts"
import { logInUser, logOutUser, signUpNewUser } from "./utils/user.ts"

test.use({ storageState: anonymousStorageState })

test("auth_login_with_valid_credentials_opens_overview", async ({ page }) => {
  // Arrange / Act
  await logInUser(page, firstSuperuser, firstSuperuserPassword)

  // Assert
  await expect(page).toHaveURL(/\/overview$/)
})

test("auth_logout_clears_session_and_redirects_to_login", async ({ page }) => {
  // Arrange
  await logInUser(page, firstSuperuser, firstSuperuserPassword)

  // Act
  await logOutUser(page)

  // Assert
  await expect(page).toHaveURL(/\/login$/)
})

test("auth_logged_out_user_visiting_protected_route_redirects_to_login", async ({
  page,
}) => {
  // Arrange / Act
  await page.goto("/settings")

  // Assert
  await expect(page).toHaveURL(/\/login\?redirect=%2Fsettings$/)
})

test("auth_invalid_token_visiting_protected_route_redirects_to_login", async ({
  page,
}) => {
  // Arrange
  await page.addInitScript(() => {
    localStorage.setItem("access_token", "invalid_token")
  })

  // Act
  await page.goto("/settings")

  // Assert
  await expect(page).toHaveURL(/\/login\?redirect=%2Fsettings$/)
})

test("auth_signup_with_legal_acceptance_redirects_to_login", async ({
  page,
}) => {
  // Arrange
  const email = randomEmail()
  const password = randomPassword()

  // Act
  await signUpNewUser(page, "Test User", email, password)

  // Assert
  await expect(page).toHaveURL(/\/login$/)
})

test("auth_reset_password_link_updates_password_and_allows_login", async ({
  page,
  request,
}) => {
  // Arrange
  const email = randomEmail()
  const password = randomPassword()
  const newPassword = randomPassword()
  await signUpNewUser(page, "Test User", email, password)

  await page.goto("/login")
  const appOrigin = new URL(page.url()).origin
  const recoveryUrl = await getPasswordRecoveryLink({
    request,
    email,
    appOrigin,
  })

  // Act
  await page.goto(recoveryUrl)
  await page.getByPlaceholder("New Password").fill(newPassword)
  await page.getByPlaceholder("Confirm Password").fill(newPassword)
  await page.getByRole("button", { name: "Reset Password" }).click()

  // Assert
  await expect(page.getByText("Password updated successfully")).toBeVisible()
  await logInUser(page, email, newPassword)
})

test("auth_invalid_reset_password_token_shows_backend_error", async ({
  page,
}) => {
  // Arrange
  const password = randomPassword()

  // Act
  await page.goto("/reset-password?token=invalidtoken")
  await page.getByPlaceholder("New Password").fill(password)
  await page.getByPlaceholder("Confirm Password").fill(password)
  await page.getByRole("button", { name: "Reset Password" }).click()

  // Assert
  await expect(page.getByText("Invalid token")).toBeVisible()
})
