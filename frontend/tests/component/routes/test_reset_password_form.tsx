import { screen, waitFor } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import { beforeEach, describe, expect, test, vi } from "vitest"

import { LoginService } from "../../../src/client"
import { renderWithProviders } from "../helpers/render"

const navigate = vi.fn()
const toast = {
  showSuccessToast: vi.fn(),
  showErrorToast: vi.fn(),
}

vi.mock("@tanstack/react-router", () => ({
  createFileRoute: () => (config: unknown) => config,
  redirect: vi.fn(),
  useNavigate: () => navigate,
}))

vi.mock("@/hooks/useCustomToast", () => ({
  default: () => toast,
}))

const { RecoverPasswordPage } = await import(
  "../../../src/routes/-components/RecoverPasswordPage"
)
const { ResetPasswordPage } = await import(
  "../../../src/routes/-components/ResetPasswordPage"
)

describe("recover and reset password forms", () => {
  beforeEach(() => {
    vi.restoreAllMocks()
    navigate.mockClear()
    toast.showSuccessToast.mockClear()
    toast.showErrorToast.mockClear()
    window.history.replaceState(null, "", "/")
  })

  test("recover_password_empty_email_shows_required_validation_error", async () => {
    // Arrange
    const user = userEvent.setup()
    renderWithProviders(<RecoverPasswordPage />)

    // Act
    await user.click(screen.getByRole("button", { name: "Continue" }))

    // Assert
    expect(await screen.findByText("Email is required")).toBeVisible()
  })

  test("recover_password_valid_email_calls_recovery_and_shows_success", async () => {
    // Arrange
    const user = userEvent.setup()
    vi.spyOn(LoginService, "recoverPassword").mockResolvedValue(
      undefined as never,
    )
    renderWithProviders(<RecoverPasswordPage />)

    // Act
    await user.type(screen.getByPlaceholderText("Email"), "user@example.com")
    await user.click(screen.getByRole("button", { name: "Continue" }))

    // Assert
    await waitFor(() => {
      expect(LoginService.recoverPassword).toHaveBeenCalledWith({
        email: "user@example.com",
      })
    })
    expect(toast.showSuccessToast).toHaveBeenCalledWith(
      "Password recovery email sent successfully.",
    )
  })

  test("reset_password_missing_token_does_not_call_api", async () => {
    // Arrange
    const user = userEvent.setup()
    const resetPassword = vi
      .spyOn(LoginService, "resetPassword")
      .mockResolvedValue(undefined as never)
    renderWithProviders(<ResetPasswordPage />)

    // Act
    await user.type(screen.getByPlaceholderText("New Password"), "Aa1!valid")
    await user.type(
      screen.getByPlaceholderText("Confirm Password"),
      "Aa1!valid",
    )
    await user.click(screen.getByRole("button", { name: "Reset Password" }))

    // Assert
    await waitFor(() => {
      expect(resetPassword).not.toHaveBeenCalled()
    })
  })

  test("reset_password_invalid_password_and_mismatch_show_validation_errors", async () => {
    // Arrange
    const user = userEvent.setup()
    renderWithProviders(<ResetPasswordPage />)

    // Act
    await user.type(screen.getByPlaceholderText("New Password"), "weak")
    await user.type(
      screen.getByPlaceholderText("Confirm Password"),
      "different",
    )
    await user.click(screen.getByRole("button", { name: "Reset Password" }))

    // Assert
    expect(
      await screen.findByText("Password must be between 8 and 25 characters"),
    ).toBeVisible()
    expect(await screen.findByText("The passwords do not match")).toBeVisible()
  })

  test("reset_password_valid_token_calls_api_and_navigates_to_login", async () => {
    // Arrange
    const user = userEvent.setup()
    window.history.replaceState(null, "", "/reset-password?token=reset-token")
    vi.spyOn(LoginService, "resetPassword").mockResolvedValue(
      undefined as never,
    )
    renderWithProviders(<ResetPasswordPage />)

    // Act
    await user.type(screen.getByPlaceholderText("New Password"), "Aa1!valid")
    await user.type(
      screen.getByPlaceholderText("Confirm Password"),
      "Aa1!valid",
    )
    await user.click(screen.getByRole("button", { name: "Reset Password" }))

    // Assert
    await waitFor(() => {
      expect(LoginService.resetPassword).toHaveBeenCalledWith({
        requestBody: {
          new_password: "Aa1!valid",
          token: "reset-token",
        },
      })
    })
    expect(navigate).toHaveBeenCalledWith({ to: "/login" })
  })
})
