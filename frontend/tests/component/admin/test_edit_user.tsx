import { screen, waitFor } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import { beforeEach, describe, expect, test, vi } from "vitest"

import type { AdminUserPublic } from "../../../src/client"
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

const EditUser = (await import("../../../src/components/Admin/EditUser"))
  .default

const createUser = (
  overrides: Partial<AdminUserPublic> = {},
): AdminUserPublic => ({
  access_profile: "standard",
  billing_eligible: true,
  email: "edit@example.com",
  full_name: "Edit User",
  id: "user-edit",
  is_active: true,
  is_superuser: false,
  managed_access_source: null,
  plan_status: "base",
  ...overrides,
})

const createApiError = (detail: string) =>
  new ApiError(
    { method: "PATCH", url: "/api/v1/users/user-edit" } as never,
    {
      body: { detail },
      ok: false,
      status: 400,
      statusText: "Bad Request",
      url: "/api/v1/users/user-edit",
    },
    detail,
  )

describe("edit user admin dialog", () => {
  beforeEach(() => {
    toast.showErrorToast.mockClear()
    toast.showSuccessToast.mockClear()
    vi.restoreAllMocks()
  })

  test("edit_user_initial_state_renders_current_values", async () => {
    // Arrange
    const user = userEvent.setup()

    // Act
    renderWithProviders(<EditUser user={createUser()} />)
    await user.click(screen.getByRole("button", { name: "Edit User" }))

    // Assert
    expect(await screen.findByDisplayValue("edit@example.com")).toBeVisible()
    expect(screen.getByDisplayValue("Edit User")).toBeVisible()
    expect(screen.getByLabelText("Access Profile")).toHaveValue("standard")
  })

  test("edit_user_ambassador_disables_superuser_transition", async () => {
    // Arrange
    const user = userEvent.setup()

    // Act
    renderWithProviders(
      <EditUser user={createUser({ access_profile: "ambassador" })} />,
    )
    await user.click(screen.getByRole("button", { name: "Edit User" }))

    // Assert
    expect(screen.getByLabelText("Is superuser?")).toBeDisabled()
    expect(
      screen.getByText(
        "Move the user to Standard and save before switching to Superuser or Ambassador.",
      ),
    ).toBeVisible()
  })

  test("edit_user_cancel_closes_dialog_without_update", async () => {
    // Arrange
    const user = userEvent.setup()
    const updateUser = vi.spyOn(UsersService, "updateUser")
    renderWithProviders(<EditUser user={createUser()} />)

    // Act
    await user.click(screen.getByRole("button", { name: "Edit User" }))
    await user.clear(await screen.findByLabelText("Full Name"))
    await user.type(screen.getByLabelText("Full Name"), "Changed User")
    await user.click(screen.getByRole("button", { name: "Cancel" }))

    // Assert
    expect(updateUser).not.toHaveBeenCalled()
    expect(
      screen.queryByText("Update the user details below."),
    ).not.toBeInTheDocument()
  })

  test("edit_user_success_omits_confirm_password_and_empty_password", async () => {
    // Arrange
    const user = userEvent.setup()
    vi.spyOn(UsersService, "updateUser").mockResolvedValue(
      createUser({ email: "updated@example.com", full_name: "Updated User" }),
    )
    const { queryClient } = renderWithProviders(
      <EditUser user={createUser()} />,
    )
    const invalidateQueries = vi.spyOn(queryClient, "invalidateQueries")

    // Act
    await user.click(screen.getByRole("button", { name: "Edit User" }))
    await user.clear(await screen.findByPlaceholderText("Email"))
    await user.type(screen.getByPlaceholderText("Email"), "updated@example.com")
    await user.clear(screen.getByPlaceholderText("Full name"))
    await user.type(screen.getByPlaceholderText("Full name"), "Updated User")
    await user.click(screen.getByRole("button", { name: "Save" }))

    // Assert
    await waitFor(() => {
      expect(UsersService.updateUser).toHaveBeenCalledWith({
        requestBody: expect.not.objectContaining({
          confirm_password: expect.anything(),
          password: "",
        }),
        userId: "user-edit",
      })
      expect(invalidateQueries).toHaveBeenCalledWith({ queryKey: ["users"] })
    })
    expect(toast.showSuccessToast).toHaveBeenCalledWith(
      "User updated successfully.",
    )
  })

  test("edit_user_backend_error_shows_error_toast", async () => {
    // Arrange
    const user = userEvent.setup()
    vi.spyOn(UsersService, "updateUser").mockRejectedValue(
      createApiError("Email already exists"),
    )
    renderWithProviders(<EditUser user={createUser()} />)

    // Act
    await user.click(screen.getByRole("button", { name: "Edit User" }))
    await user.clear(await screen.findByPlaceholderText("Email"))
    await user.type(screen.getByPlaceholderText("Email"), "taken@example.com")
    await user.click(screen.getByRole("button", { name: "Save" }))

    // Assert
    await waitFor(() => {
      expect(toast.showErrorToast).toHaveBeenCalledWith("Email already exists")
    })
  })
})
