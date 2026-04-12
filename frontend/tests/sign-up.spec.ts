import { expect, type Page, test } from "@playwright/test"

import { randomEmail, randomPassword } from "./utils/random"
import { anonymousStorageState } from "./utils/storageState"

test.use({ storageState: anonymousStorageState })

type OptionsType = {
  exact?: boolean
}

const fillForm = async (
  page: Page,
  full_name: string,
  email: string,
  password: string,
  confirm_password: string,
) => {
  await page.getByPlaceholder("Full Name").fill(full_name)
  await page.getByPlaceholder("Email").fill(email)
  await page.getByPlaceholder("Password", { exact: true }).fill(password)
  await page.getByPlaceholder("Confirm Password").fill(confirm_password)
}

const openLegalModal = async (page: Page) => {
  await page.getByRole("button", { name: "Sign Up" }).click()
  await expect(page.getByTestId("signup-legal-modal")).toBeVisible()
}

const acceptLegalDocuments = async (page: Page) => {
  await page.getByTestId("accept-privacy-checkbox").click()
  await page.getByTestId("accept-terms-checkbox").click()
  await page.getByTestId("confirm-legal-acceptance").click()
}

const verifyInput = async (
  page: Page,
  placeholder: string,
  options?: OptionsType,
) => {
  const input = page.getByPlaceholder(placeholder, options)
  await expect(input).toBeVisible()
  await expect(input).toHaveText("")
  await expect(input).toBeEditable()
}

test("Inputs are visible, empty and editable", async ({ page }) => {
  await page.goto("/signup")

  await verifyInput(page, "Full Name")
  await verifyInput(page, "Email")
  await verifyInput(page, "Password", { exact: true })
  await verifyInput(page, "Confirm Password")
})

test("Sign Up button is visible", async ({ page }) => {
  await page.goto("/signup")

  await expect(page.getByRole("button", { name: "Sign Up" })).toBeVisible()
})

test("Log In link is visible", async ({ page }) => {
  await page.goto("/signup")

  await expect(page.getByRole("link", { name: "Log In" })).toBeVisible()
})

test("Sign up with valid name, email, and password", async ({ page }) => {
  const full_name = "Test User"
  const email = randomEmail()
  const password = randomPassword()

  await page.goto("/signup")
  await fillForm(page, full_name, email, password, password)
  await openLegalModal(page)
  await acceptLegalDocuments(page)
  await expect(page).toHaveURL(/\/login$/)
})

test("Sign up with invalid email", async ({ page }) => {
  await page.goto("/signup")

  await fillForm(
    page,
    "Playwright Test",
    "invalid-email",
    "Valid1!Pass",
    "Valid1!Pass",
  )
  await page.getByRole("button", { name: "Sign Up" }).click()

  await expect(page.getByText("Invalid email address")).toBeVisible()
  await expect(page.getByTestId("signup-legal-modal")).toBeHidden()
})

test("Sign up with existing email", async ({ page }) => {
  const fullName = "Test User"
  const email = randomEmail()
  const password = randomPassword()

  // Sign up with an email
  await page.goto("/signup")

  await fillForm(page, fullName, email, password, password)
  await openLegalModal(page)
  await acceptLegalDocuments(page)

  // Sign up again with the same email
  await page.goto("/signup")

  await fillForm(page, fullName, email, password, password)
  await openLegalModal(page)
  await acceptLegalDocuments(page)

  await expect(
    page.getByText("The user with this email already exists in the system"),
  ).toBeVisible()
})

test("Sign up with weak password", async ({ page }) => {
  const fullName = "Test User"
  const email = randomEmail()
  const password = "weak"

  await page.goto("/signup")

  await fillForm(page, fullName, email, password, password)
  await page.getByRole("button", { name: "Sign Up" }).click()

  await expect(
    page.getByText("Password must be between 8 and 25 characters"),
  ).toBeVisible()
  await expect(page.getByTestId("signup-legal-modal")).toBeHidden()
})

test("Password requirements checklist updates on sign up", async ({ page }) => {
  await page.goto("/signup")

  const passwordInput = page.getByPlaceholder("Password", { exact: true })

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

test("Sign up with mismatched passwords", async ({ page }) => {
  const fullName = "Test User"
  const email = randomEmail()
  const password = randomPassword()
  const password2 = randomPassword()

  await page.goto("/signup")

  await fillForm(page, fullName, email, password, password2)
  await page.getByRole("button", { name: "Sign Up" }).click()

  await expect(page.getByText("Passwords do not match")).toBeVisible()
  await expect(page.getByTestId("signup-legal-modal")).toBeHidden()
})

test("Sign up with missing full name", async ({ page }) => {
  const fullName = ""
  const email = randomEmail()
  const password = randomPassword()

  await page.goto("/signup")

  await fillForm(page, fullName, email, password, password)
  await page.getByRole("button", { name: "Sign Up" }).click()

  await expect(page.getByText("Full Name is required")).toBeVisible()
  await expect(page.getByTestId("signup-legal-modal")).toBeHidden()
})

test("Sign up with missing email", async ({ page }) => {
  const fullName = "Test User"
  const email = ""
  const password = randomPassword()

  await page.goto("/signup")

  await fillForm(page, fullName, email, password, password)
  await page.getByRole("button", { name: "Sign Up" }).click()

  await expect(page.getByText("Email is required")).toBeVisible()
  await expect(page.getByTestId("signup-legal-modal")).toBeHidden()
})

test("Sign up with missing password", async ({ page }) => {
  const fullName = ""
  const email = randomEmail()
  const password = ""

  await page.goto("/signup")

  await fillForm(page, fullName, email, password, password)
  await page.getByRole("button", { name: "Sign Up" }).click()

  await expect(page.getByText("Password is required")).toBeVisible()
  await expect(page.getByTestId("signup-legal-modal")).toBeHidden()
})

test("Legal acceptance confirm button stays disabled until both checkboxes are checked", async ({
  page,
}) => {
  await page.goto("/signup")

  await fillForm(page, "Test User", randomEmail(), "Valid1!Pass", "Valid1!Pass")
  await openLegalModal(page)

  const confirmButton = page.getByTestId("confirm-legal-acceptance")

  await expect(confirmButton).toBeDisabled()
  await page.getByTestId("accept-privacy-checkbox").click()
  await expect(confirmButton).toBeDisabled()
  await page.getByTestId("accept-terms-checkbox").click()
  await expect(confirmButton).toBeEnabled()
})

test("Legal modal content renders above its backdrop", async ({ page }) => {
  await page.goto("/signup")

  await fillForm(page, "Test User", randomEmail(), "Valid1!Pass", "Valid1!Pass")
  await openLegalModal(page)

  const layering = await page.evaluate(() => {
    const modal = document.querySelector("[data-testid='signup-legal-modal']")
    const backdrop = document.querySelector(
      "[data-scope='dialog'][data-part='backdrop']",
    )

    if (!modal || !backdrop) {
      return null
    }

    const modalZIndex = Number.parseInt(getComputedStyle(modal).zIndex, 10)
    const backdropZIndex = Number.parseInt(
      getComputedStyle(backdrop).zIndex,
      10,
    )

    return {
      modalZIndex: Number.isNaN(modalZIndex) ? null : modalZIndex,
      backdropZIndex: Number.isNaN(backdropZIndex) ? null : backdropZIndex,
    }
  })

  expect(layering).not.toBeNull()
  expect(layering?.modalZIndex).not.toBeNull()
  expect(layering?.backdropZIndex).not.toBeNull()
  expect(layering!.modalZIndex!).toBeGreaterThan(layering!.backdropZIndex!)
})

test("Legal document links open in a new tab", async ({ page, context }) => {
  await page.goto("/signup")

  await fillForm(page, "Test User", randomEmail(), "Valid1!Pass", "Valid1!Pass")
  await openLegalModal(page)

  const privacyPopupPromise = context.waitForEvent("page")
  await page.getByTestId("privacy-link").click()
  const privacyPopup = await privacyPopupPromise
  await privacyPopup.waitForURL(/\/privacy$/)

  const termsPopupPromise = context.waitForEvent("page")
  await page.getByTestId("terms-link").click()
  const termsPopup = await termsPopupPromise
  await termsPopup.waitForURL(/\/terms-conditions$/)
})
