import { screen, waitFor } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import { beforeEach, describe, expect, test, vi } from "vitest"

import { UsersService } from "../../../src/client"
import { ApiError } from "../../../src/client/core/ApiError"
import { renderWithProviders } from "../helpers/render"

const { toast } = vi.hoisted(() => ({
  toast: {
    showErrorToast: vi.fn(),
    showSuccessToast: vi.fn(),
  },
}))

vi.mock("@/hooks/useCustomToast", () => ({
  default: () => toast,
}))

const ChangePassword = (
  await import("../../../src/components/UserSettings/ChangePassword")
).default

const createApiError = (detail: string) =>
  new ApiError(
    {
      method: "PATCH",
      url: "/api/v1/users/me/password",
    } as never,
    {
      body: { detail },
      ok: false,
      status: 400,
      statusText: "Bad Request",
      url: "/api/v1/users/me/password",
    },
    detail,
  )

describe("change password settings", () => {
  beforeEach(() => {
    toast.showErrorToast.mockClear()
    toast.showSuccessToast.mockClear()
    vi.restoreAllMocks()
  })

  test("change_password_weak_new_password_shows_validation_error", async () => {
    // Arrange
    const user = userEvent.setup()
    const updatePasswordMe = vi.spyOn(UsersService, "updatePasswordMe")
    renderWithProviders(<ChangePassword />)

    // Act
    await user.type(screen.getByPlaceholderText("Current Password"), "old-pass")
    await user.type(screen.getByPlaceholderText("New Password"), "weak")
    await user.type(screen.getByPlaceholderText("Confirm Password"), "weak")
    await user.click(screen.getByRole("button", { name: "Save" }))

    // Assert
    expect(
      await screen.findByText("Password must be between 8 and 25 characters"),
    ).toBeVisible()
    expect(updatePasswordMe).not.toHaveBeenCalled()
  })

  test("change_password_mismatched_confirmation_shows_validation_error", async () => {
    // Arrange
    const user = userEvent.setup()
    const updatePasswordMe = vi.spyOn(UsersService, "updatePasswordMe")
    renderWithProviders(<ChangePassword />)

    // Act
    await user.type(screen.getByPlaceholderText("Current Password"), "old-pass")
    await user.type(screen.getByPlaceholderText("New Password"), "Aa1!valid")
    await user.type(
      screen.getByPlaceholderText("Confirm Password"),
      "Aa1!different",
    )
    await user.click(screen.getByRole("button", { name: "Save" }))

    // Assert
    expect(await screen.findByText("The passwords do not match")).toBeVisible()
    expect(updatePasswordMe).not.toHaveBeenCalled()
  })

  test("change_password_success_calls_api_and_shows_success_toast", async () => {
    // Arrange
    const user = userEvent.setup()
    vi.spyOn(UsersService, "updatePasswordMe").mockResolvedValue(
      undefined as never,
    )
    renderWithProviders(<ChangePassword />)

    // Act
    await user.type(screen.getByPlaceholderText("Current Password"), "old-pass")
    await user.type(screen.getByPlaceholderText("New Password"), "Aa1!valid")
    await user.type(
      screen.getByPlaceholderText("Confirm Password"),
      "Aa1!valid",
    )
    await user.click(screen.getByRole("button", { name: "Save" }))

    // Assert
    await waitFor(() => {
      expect(UsersService.updatePasswordMe).toHaveBeenCalledWith({
        requestBody: expect.objectContaining({
          current_password: "old-pass",
          new_password: "Aa1!valid",
        }),
      })
    })
    expect(toast.showSuccessToast).toHaveBeenCalledWith(
      "Password updated successfully.",
    )
  })

  test("change_password_invalid_current_password_shows_backend_error_toast", async () => {
    // Arrange
    const user = userEvent.setup()
    vi.spyOn(UsersService, "updatePasswordMe").mockRejectedValue(
      createApiError("Incorrect password"),
    )
    renderWithProviders(<ChangePassword />)

    // Act
    await user.type(screen.getByPlaceholderText("Current Password"), "bad-pass")
    await user.type(screen.getByPlaceholderText("New Password"), "Aa1!valid")
    await user.type(
      screen.getByPlaceholderText("Confirm Password"),
      "Aa1!valid",
    )
    await user.click(screen.getByRole("button", { name: "Save" }))

    // Assert
    await waitFor(() => {
      expect(toast.showErrorToast).toHaveBeenCalledWith("Incorrect password")
    })
  })

  test("change_password_current_equals_new_password_backend_error_shows_toast", async () => {
    // Arrange
    const user = userEvent.setup()
    vi.spyOn(UsersService, "updatePasswordMe").mockRejectedValue(
      createApiError("New password cannot be the same as the current one"),
    )
    renderWithProviders(<ChangePassword />)

    // Act
    await user.type(screen.getByPlaceholderText("Current Password"), "Aa1!same")
    await user.type(screen.getByPlaceholderText("New Password"), "Aa1!same")
    await user.type(screen.getByPlaceholderText("Confirm Password"), "Aa1!same")
    await user.click(screen.getByRole("button", { name: "Save" }))

    // Assert
    await waitFor(() => {
      expect(toast.showErrorToast).toHaveBeenCalledWith(
        "New password cannot be the same as the current one",
      )
    })
  })
})
