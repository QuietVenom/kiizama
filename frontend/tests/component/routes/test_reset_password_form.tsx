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

vi.mock("@/components/Common/ThemeLogo", () => ({
  default: () => <span>Kiizama</span>,
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
    await user.click(screen.getByRole("button", { name: "Continuar" }))

    // Assert
    expect(
      await screen.findByText("El correo electrónico es obligatorio"),
    ).toBeVisible()
  })

  test("recover_password_valid_email_calls_recovery_and_shows_success", async () => {
    // Arrange
    const user = userEvent.setup()
    vi.spyOn(LoginService, "recoverPassword").mockResolvedValue(
      undefined as never,
    )
    renderWithProviders(<RecoverPasswordPage />)

    // Act
    await user.type(
      screen.getByPlaceholderText("Correo electrónico"),
      "user@example.com",
    )
    await user.click(screen.getByRole("button", { name: "Continuar" }))

    // Assert
    await waitFor(() => {
      expect(LoginService.recoverPassword).toHaveBeenCalledWith({
        email: "user@example.com",
      })
    })
    expect(toast.showSuccessToast).toHaveBeenCalledWith(
      "El correo de recuperación de contraseña se envió correctamente.",
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
    await user.type(
      screen.getByPlaceholderText("Nueva contraseña"),
      "Aa1!valid",
    )
    await user.type(
      screen.getByPlaceholderText("Confirmar contraseña"),
      "Aa1!valid",
    )
    await user.click(
      screen.getByRole("button", { name: "Restablecer contraseña" }),
    )

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
    await user.type(screen.getByPlaceholderText("Nueva contraseña"), "weak")
    await user.type(
      screen.getByPlaceholderText("Confirmar contraseña"),
      "different",
    )
    await user.click(
      screen.getByRole("button", { name: "Restablecer contraseña" }),
    )

    // Assert
    expect(
      await screen.findByText(
        "La contraseña debe tener entre 8 y 25 caracteres",
      ),
    ).toBeVisible()
    expect(
      await screen.findByText("Las contraseñas no coinciden"),
    ).toBeVisible()
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
    await user.type(
      screen.getByPlaceholderText("Nueva contraseña"),
      "Aa1!valid",
    )
    await user.type(
      screen.getByPlaceholderText("Confirmar contraseña"),
      "Aa1!valid",
    )
    await user.click(
      screen.getByRole("button", { name: "Restablecer contraseña" }),
    )

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
    expect(toast.showSuccessToast).toHaveBeenCalledWith(
      "La contraseña se actualizó correctamente.",
    )
  })
})
