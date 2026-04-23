import { screen, waitFor } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import { beforeEach, describe, expect, test, vi } from "vitest"

import { UsersService } from "../../../src/client"
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

const DeleteUser = (await import("../../../src/components/Admin/DeleteUser"))
  .default

const deleteUserId = "user-delete"

describe("delete user admin dialog", () => {
  beforeEach(() => {
    toast.showErrorToast.mockClear()
    toast.showSuccessToast.mockClear()
    vi.restoreAllMocks()
  })

  test("delete_user_cancel_closes_dialog_without_calling_api", async () => {
    // Arrange
    const user = userEvent.setup()
    const deleteUser = vi.spyOn(UsersService, "deleteUser")
    renderWithProviders(<DeleteUser id={deleteUserId} />)

    // Act
    await user.click(screen.getByRole("button", { name: "Delete User" }))
    await user.click(await screen.findByRole("button", { name: "Cancel" }))

    // Assert
    expect(deleteUser).not.toHaveBeenCalled()
    await waitFor(() => {
      expect(screen.queryByText(/permanently deleted/i)).not.toBeInTheDocument()
    })
  })

  test("delete_user_success_calls_api_invalidates_queries_and_shows_toast", async () => {
    // Arrange
    const user = userEvent.setup()
    vi.spyOn(UsersService, "deleteUser").mockResolvedValue(undefined as never)
    const { queryClient } = renderWithProviders(
      <DeleteUser id={deleteUserId} />,
    )
    const invalidateQueries = vi.spyOn(queryClient, "invalidateQueries")

    // Act
    await user.click(screen.getByRole("button", { name: "Delete User" }))
    await user.click(await screen.findByRole("button", { name: "Delete" }))

    // Assert
    await waitFor(() => {
      expect(UsersService.deleteUser).toHaveBeenCalledWith({
        userId: deleteUserId,
      })
      expect(invalidateQueries).toHaveBeenCalled()
    })
    expect(toast.showSuccessToast).toHaveBeenCalledWith(
      "The user was deleted successfully",
    )
  })

  test("delete_user_error_shows_error_toast", async () => {
    // Arrange
    const user = userEvent.setup()
    vi.spyOn(UsersService, "deleteUser").mockRejectedValue(new Error("boom"))
    renderWithProviders(<DeleteUser id={deleteUserId} />)

    // Act
    await user.click(screen.getByRole("button", { name: "Delete User" }))
    await user.click(await screen.findByRole("button", { name: "Delete" }))

    // Assert
    await waitFor(() => {
      expect(toast.showErrorToast).toHaveBeenCalledWith(
        "An error occurred while deleting the user",
      )
    })
  })
})
