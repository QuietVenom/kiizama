import { screen, waitFor } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import { beforeEach, describe, expect, test, vi } from "vitest"

import { UsersService } from "../../../src/client"
import { ApiError } from "../../../src/client/core/ApiError"
import { renderWithProviders } from "../helpers/render"

const { authState, toast } = vi.hoisted(() => ({
  authState: {
    user: {
      id: "user-1",
      email: "user@example.com",
      full_name: "Test User",
      is_active: true,
      is_superuser: false,
    },
  },
  toast: {
    showErrorToast: vi.fn(),
    showSuccessToast: vi.fn(),
  },
}))

vi.mock("@/hooks/useAuth", () => ({
  currentUserQueryOptions: { queryKey: ["currentUser"] },
  default: () => authState,
}))

vi.mock("@/hooks/useCustomToast", () => ({
  default: () => toast,
}))

const UserInformation = (
  await import("../../../src/components/UserSettings/UserInformation")
).default

const createApiError = (detail: string) =>
  new ApiError(
    {
      method: "PATCH",
      url: "/api/v1/users/me",
    } as never,
    {
      body: { detail },
      ok: false,
      status: 400,
      statusText: "Bad Request",
      url: "/api/v1/users/me",
    },
    detail,
  )

describe("user information settings", () => {
  beforeEach(() => {
    authState.user = {
      id: "user-1",
      email: "user@example.com",
      full_name: "Test User",
      is_active: true,
      is_superuser: false,
    }
    toast.showErrorToast.mockClear()
    toast.showSuccessToast.mockClear()
    vi.restoreAllMocks()
  })

  test("user_information_initial_state_renders_name_and_email", () => {
    // Arrange / Act
    renderWithProviders(<UserInformation />)

    // Assert
    expect(screen.getByText("Test User")).toBeVisible()
    expect(screen.getByText("user@example.com")).toBeVisible()
  })

  test("user_information_cancel_edit_restores_original_values", async () => {
    // Arrange
    const user = userEvent.setup()
    renderWithProviders(<UserInformation />)

    // Act
    await user.click(screen.getByRole("button", { name: "Editar" }))
    await user.clear(screen.getByLabelText("Nombre completo"))
    await user.type(screen.getByLabelText("Nombre completo"), "Changed User")
    await user.clear(screen.getByLabelText("Correo electrónico"))
    await user.type(
      screen.getByLabelText("Correo electrónico"),
      "changed@example.com",
    )
    await user.click(screen.getByRole("button", { name: "Cancelar" }))

    // Assert
    expect(screen.getByText("Test User")).toBeVisible()
    expect(screen.getByText("user@example.com")).toBeVisible()
  })

  test("user_information_invalid_email_shows_validation_error_without_submitting", async () => {
    // Arrange
    const user = userEvent.setup()
    const updateUserMe = vi.spyOn(UsersService, "updateUserMe")
    renderWithProviders(<UserInformation />)

    // Act
    await user.click(screen.getByRole("button", { name: "Editar" }))
    await user.clear(screen.getByLabelText("Correo electrónico"))
    await user.type(screen.getByLabelText("Correo electrónico"), "bad-email")
    await user.click(screen.getByRole("button", { name: "Guardar" }))

    // Assert
    expect(await screen.findByText("Correo electrónico inválido")).toBeVisible()
    expect(updateUserMe).not.toHaveBeenCalled()
  })

  test("user_information_success_updates_query_and_shows_success_toast", async () => {
    // Arrange
    const user = userEvent.setup()
    const updatedUser = {
      ...authState.user,
      email: "updated@example.com",
      full_name: "Updated User",
    }
    vi.spyOn(UsersService, "updateUserMe").mockImplementation(((
      data: Parameters<typeof UsersService.updateUserMe>[0],
    ) => {
      const { requestBody } = data
      authState.user = {
        ...authState.user,
        ...requestBody,
      } as typeof authState.user
      return updatedUser as never
    }) as never)
    renderWithProviders(<UserInformation />)

    // Act
    await user.click(screen.getByRole("button", { name: "Editar" }))
    await user.clear(screen.getByLabelText("Nombre completo"))
    await user.type(screen.getByLabelText("Nombre completo"), "Updated User")
    await user.clear(screen.getByLabelText("Correo electrónico"))
    await user.type(
      screen.getByLabelText("Correo electrónico"),
      "updated@example.com",
    )
    await user.click(screen.getByRole("button", { name: "Guardar" }))

    // Assert
    await waitFor(() => {
      expect(UsersService.updateUserMe).toHaveBeenCalledWith({
        requestBody: expect.objectContaining({
          email: "updated@example.com",
          full_name: "Updated User",
        }),
      })
    })
    expect(toast.showSuccessToast).toHaveBeenCalledWith(
      "La información del usuario se actualizó correctamente.",
    )
    expect(await screen.findByText("Updated User")).toBeVisible()
    expect(screen.getByText("updated@example.com")).toBeVisible()
  })

  test("user_information_backend_validation_error_shows_error_toast", async () => {
    // Arrange
    const user = userEvent.setup()
    vi.spyOn(UsersService, "updateUserMe").mockRejectedValue(
      createApiError("Email already exists"),
    )
    renderWithProviders(<UserInformation />)

    // Act
    await user.click(screen.getByRole("button", { name: "Editar" }))
    await user.clear(screen.getByLabelText("Nombre completo"))
    await user.type(
      screen.getByLabelText("Nombre completo"),
      "Test User Edited",
    )
    await user.clear(screen.getByLabelText("Correo electrónico"))
    await user.type(
      screen.getByLabelText("Correo electrónico"),
      "taken@example.com",
    )
    const saveButton = screen.getByRole("button", { name: "Guardar" })
    await waitFor(() => {
      expect(saveButton).toBeEnabled()
    })
    await user.click(saveButton)

    // Assert
    await waitFor(() => {
      expect(UsersService.updateUserMe).toHaveBeenCalled()
      expect(toast.showErrorToast).toHaveBeenCalledWith("Email already exists")
    })
  })
})
