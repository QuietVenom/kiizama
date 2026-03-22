import { expect, test } from "@playwright/test"
import { getPasswordRecoveryLink } from "./utils/passwordRecovery"
import { randomEmail, randomPassword } from "./utils/random"
import { anonymousStorageState } from "./utils/storageState"
import { logInUser, signUpNewUser } from "./utils/user"

test.use({ storageState: anonymousStorageState })

test("Password Recovery title is visible", async ({ page }) => {
  await page.goto("/recover-password")

  await expect(
    page.getByRole("heading", { name: "Password Recovery" }),
  ).toBeVisible()
})

test("Input is visible, empty and editable", async ({ page }) => {
  await page.goto("/recover-password")

  await expect(page.getByPlaceholder("Email")).toBeVisible()
  await expect(page.getByPlaceholder("Email")).toHaveText("")
  await expect(page.getByPlaceholder("Email")).toBeEditable()
})

test("Continue button is visible", async ({ page }) => {
  await page.goto("/recover-password")

  await expect(page.getByRole("button", { name: "Continue" })).toBeVisible()
})

test("User can reset password successfully using the link", async ({
  page,
  request,
}) => {
  const fullName = "Test User"
  const email = randomEmail()
  const password = randomPassword()
  const newPassword = randomPassword()

  // Sign up a new user
  await signUpNewUser(page, fullName, email, password)

  await page.goto("/login")
  const appOrigin = new URL(page.url()).origin
  const url = await getPasswordRecoveryLink({
    request,
    email,
    appOrigin,
  })

  // Set the new password and confirm it
  await page.goto(url)

  await page.getByPlaceholder("New Password").fill(newPassword)
  await page.getByPlaceholder("Confirm Password").fill(newPassword)
  await page.getByRole("button", { name: "Reset Password" }).click()
  await expect(page.getByText("Password updated successfully")).toBeVisible()

  // Check if the user is able to login with the new password
  await logInUser(page, email, newPassword)
})

test("Expired or invalid reset link", async ({ page }) => {
  const password = randomPassword()
  const invalidUrl = "/reset-password?token=invalidtoken"

  await page.goto(invalidUrl)

  await page.getByPlaceholder("New Password").fill(password)
  await page.getByPlaceholder("Confirm Password").fill(password)
  await page.getByRole("button", { name: "Reset Password" }).click()

  await expect(page.getByText("Invalid token")).toBeVisible()
})

test("Weak new password validation", async ({ page, request }) => {
  const fullName = "Test User"
  const email = randomEmail()
  const password = randomPassword()
  const weakPassword = "123"

  // Sign up a new user
  await signUpNewUser(page, fullName, email, password)

  await page.goto("/login")
  const appOrigin = new URL(page.url()).origin
  const url = await getPasswordRecoveryLink({
    request,
    email,
    appOrigin,
  })

  // Set a weak new password
  await page.goto(url)
  await page.getByPlaceholder("New Password").fill(weakPassword)
  await page.getByPlaceholder("Confirm Password").fill(weakPassword)
  await page.getByRole("button", { name: "Reset Password" }).click()

  await expect(
    page.getByText("Password must be between 8 and 25 characters"),
  ).toBeVisible()
})

test("Password requirements checklist updates on reset password", async ({
  page,
}) => {
  await page.goto("/reset-password?token=invalidtoken")

  const passwordInput = page.getByPlaceholder("New Password")

  await expect(page.getByTestId("password-requirement-length")).toHaveAttribute(
    "data-satisfied",
    "false",
  )

  await passwordInput.fill("Abcdef1!")

  await expect(page.getByTestId("password-requirement-length")).toHaveAttribute(
    "data-satisfied",
    "true",
  )
  await expect(
    page.getByTestId("password-requirement-uppercase"),
  ).toHaveAttribute("data-satisfied", "true")
  await expect(page.getByTestId("password-requirement-number")).toHaveAttribute(
    "data-satisfied",
    "true",
  )
  await expect(
    page.getByTestId("password-requirement-special"),
  ).toHaveAttribute("data-satisfied", "true")
})
