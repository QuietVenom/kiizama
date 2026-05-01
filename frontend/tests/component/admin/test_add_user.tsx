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

const AddUser = (await import("../../../src/components/Admin/AddUser")).default

const createApiError = (detail: string) =>
  new ApiError(
    { method: "POST", url: "/api/v1/users/" } as never,
    {
      body: { detail },
      ok: false,
      status: 409,
      statusText: "Conflict",
      url: "/api/v1/users/",
    },
    detail,
  )

const fillValidUserForm = async (user: ReturnType<typeof userEvent.setup>) => {
  await user.type(screen.getByPlaceholderText("Email"), "new@example.com")
  await user.tab()
  await user.type(screen.getByPlaceholderText("Full name"), "New User")
  await user.tab()
  const passwordFields = screen.getAllByPlaceholderText("Password")
  await user.type(passwordFields[0], "Strong1!")
  await user.tab()
  await user.type(passwordFields[1], "Strong1!")
  await user.tab()
}

describe("add user admin dialog", () => {
  beforeEach(() => {
    toast.showErrorToast.mockClear()
    toast.showSuccessToast.mockClear()
    vi.restoreAllMocks()
  })

  test("add_user_required_fields_keep_submit_disabled_until_valid", async () => {
    // Arrange
    const user = userEvent.setup()
    renderWithProviders(<AddUser />)

    // Act
    await user.click(screen.getByRole("button", { name: "Add User" }))

    // Assert
    expect(
      await screen.findByRole("heading", { name: "Add User" }),
    ).toBeVisible()
    expect(screen.getByRole("button", { name: "Save" })).toBeDisabled()
  })

  test("add_user_invalid_email_and_password_mismatch_show_validation_errors", async () => {
    // Arrange
    const user = userEvent.setup()
    const createUser = vi.spyOn(UsersService, "createUser")
    renderWithProviders(<AddUser />)

    // Act
    await user.click(screen.getByRole("button", { name: "Add User" }))
    await user.type(screen.getByPlaceholderText("Email"), "bad-email")
    await user.tab()
    const passwordFields = screen.getAllByPlaceholderText("Password")
    await user.type(passwordFields[0], "weak")
    await user.tab()
    await user.type(passwordFields[1], "different")
    await user.tab()

    // Assert
    expect(await screen.findByText("Invalid email address")).toBeVisible()
    expect(
      await screen.findByText("Password must be between 8 and 25 characters"),
    ).toBeVisible()
    expect(await screen.findByText("The passwords do not match")).toBeVisible()
    expect(createUser).not.toHaveBeenCalled()
  })

  test("add_user_superuser_selection_forces_standard_access", async () => {
    // Arrange
    const user = userEvent.setup()
    renderWithProviders(<AddUser />)

    // Act
    await user.click(screen.getByRole("button", { name: "Add User" }))
    await user.selectOptions(screen.getByRole("combobox"), "ambassador")
    await user.click(screen.getByLabelText("Is superuser?"))

    // Assert
    await waitFor(() => {
      expect(screen.getByRole("combobox")).toHaveValue("standard")
    })
    expect(
      screen.getByText(
        "Superusers can only be created as Standard users. Move them to Standard first before changing to Ambassador later.",
      ),
    ).toBeVisible()
  })

  test("add_user_success_calls_api_invalidates_users_and_closes_dialog", async () => {
    // Arrange
    const user = userEvent.setup()
    vi.spyOn(UsersService, "createUser").mockResolvedValue({
      email: "new@example.com",
      full_name: "New User",
      id: "user-new",
      is_active: false,
      is_superuser: false,
    })
    const { queryClient } = renderWithProviders(<AddUser />)
    const invalidateQueries = vi.spyOn(queryClient, "invalidateQueries")

    // Act
    await user.click(screen.getByRole("button", { name: "Add User" }))
    await fillValidUserForm(user)
    await waitFor(() => {
      expect(screen.getByRole("button", { name: "Save" })).toBeEnabled()
    })
    await user.click(screen.getByRole("button", { name: "Save" }))

    // Assert
    await waitFor(() => {
      expect(UsersService.createUser).toHaveBeenCalledWith({
        requestBody: expect.objectContaining({
          email: "new@example.com",
          full_name: "New User",
          password: "Strong1!",
        }),
      })
      expect(invalidateQueries).toHaveBeenCalledWith({ queryKey: ["users"] })
    })
    expect(toast.showSuccessToast).toHaveBeenCalledWith(
      "User created successfully.",
    )
    expect(screen.queryByText("Fill in the form below")).not.toBeInTheDocument()
  })

  test("add_user_conflict_error_shows_error_toast", async () => {
    // Arrange
    const user = userEvent.setup()
    vi.spyOn(UsersService, "createUser").mockRejectedValue(
      createApiError("Email already exists"),
    )
    renderWithProviders(<AddUser />)

    // Act
    await user.click(screen.getByRole("button", { name: "Add User" }))
    await fillValidUserForm(user)
    await waitFor(() => {
      expect(screen.getByRole("button", { name: "Save" })).toBeEnabled()
    })
    await user.click(screen.getByRole("button", { name: "Save" }))

    // Assert
    await waitFor(() => {
      expect(toast.showErrorToast).toHaveBeenCalledWith("Email already exists")
    })
  })
})
