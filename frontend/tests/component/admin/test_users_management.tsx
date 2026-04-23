import { QueryClient } from "@tanstack/react-query"
import { screen } from "@testing-library/react"
import { beforeEach, describe, expect, test, vi } from "vitest"

import type { AdminUserPublic, UserPublic } from "../../../src/client"
import { UsersService } from "../../../src/client"
import { renderWithProviders } from "../helpers/render"

vi.mock("@/components/Admin/AddUser", () => ({
  default: () => <button type="button">Add User</button>,
}))

vi.mock("@/components/Common/UserActionsMenu", () => ({
  UserActionsMenu: ({ disabled }: { disabled?: boolean }) => (
    <button aria-label="User actions" disabled={disabled} type="button">
      Actions
    </button>
  ),
}))

const { UsersManagementPage } = await import(
  "../../../src/routes/_layout/-components/UsersManagementPage"
)

const createAdminUser = (
  overrides: Partial<AdminUserPublic> = {},
): AdminUserPublic => ({
  access_profile: "standard",
  billing_eligible: true,
  email: "user@example.com",
  full_name: "Normal User",
  id: "user-1",
  is_active: true,
  is_superuser: false,
  managed_access_source: null,
  plan_status: "base",
  ...overrides,
})

const currentUser: UserPublic = {
  email: "current@example.com",
  full_name: "Current User",
  id: "current-user",
  is_active: true,
  is_superuser: true,
}

describe("users management admin page", () => {
  beforeEach(() => {
    vi.restoreAllMocks()
  })

  test("users_management_loading_state_renders_pending_users_table", () => {
    // Arrange
    vi.spyOn(UsersService, "readUsers").mockReturnValue(
      new Promise(() => {}) as never,
    )

    // Act
    renderWithProviders(<UsersManagementPage onPageChange={vi.fn()} page={1} />)

    // Assert
    expect(
      screen.getByRole("heading", { name: "Users Management" }),
    ).toBeVisible()
    expect(screen.getByRole("button", { name: "Add User" })).toBeVisible()
    expect(
      screen.getByRole("columnheader", { name: "Full name" }),
    ).toBeVisible()
    expect(screen.getAllByRole("row")).toHaveLength(6)
  })

  test("users_management_list_renders_users_access_labels_and_current_user_disabled_actions", async () => {
    // Arrange
    const users = [
      createAdminUser({
        email: "current@example.com",
        full_name: "Current User",
        id: "current-user",
        is_superuser: true,
        managed_access_source: "admin",
        plan_status: "none",
      }),
      createAdminUser({
        access_profile: "ambassador",
        email: "ambassador@example.com",
        full_name: null,
        id: "ambassador-user",
        is_active: false,
        managed_access_source: "ambassador",
        plan_status: "ambassador",
      }),
    ]
    vi.spyOn(UsersService, "readUsers").mockResolvedValue({
      count: users.length,
      data: users,
    })
    const queryClient = new QueryClient({
      defaultOptions: {
        mutations: { retry: false },
        queries: { gcTime: Number.POSITIVE_INFINITY, retry: false },
      },
    })
    queryClient.setQueryData(["currentUser"], currentUser)

    // Act
    renderWithProviders(
      <UsersManagementPage onPageChange={vi.fn()} page={1} />,
      { queryClient },
    )

    // Assert
    expect(await screen.findByText("Current User")).toBeVisible()
    expect(screen.getByText("current@example.com")).toBeVisible()
    expect(screen.getByText("Superuser")).toBeVisible()
    expect(screen.getByText("Admin")).toBeVisible()
    expect(screen.getByText("N/A")).toBeVisible()
    expect(screen.getByText("ambassador@example.com")).toBeVisible()
    expect(screen.getByText("Ambassador")).toBeVisible()
    expect(screen.getByText("Inactive")).toBeVisible()
    expect(
      screen.getAllByRole("button", { name: "User actions" })[0],
    ).toBeDisabled()
    expect(
      screen.getAllByRole("button", { name: "User actions" })[1],
    ).toBeEnabled()
  })
})
