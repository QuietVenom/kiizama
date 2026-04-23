import { screen } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import type { ReactNode } from "react"
import { beforeEach, describe, expect, test, vi } from "vitest"

import { renderWithProviders } from "../helpers/render"

const { authState } = vi.hoisted(() => ({
  authState: {
    logout: vi.fn(),
    user: {
      email: "user@example.com",
      full_name: "Test User",
      id: "user-1",
      is_active: true,
      is_superuser: false,
    },
  },
}))

vi.mock("@/hooks/useAuth", () => ({
  default: () => authState,
}))

vi.mock("@tanstack/react-router", () => ({
  Link: ({ children, to }: { children: ReactNode; to: string }) => (
    <a href={to}>{children}</a>
  ),
}))

const UserMenu = (await import("../../../src/components/Common/UserMenu"))
  .default

describe("user menu", () => {
  beforeEach(() => {
    authState.logout.mockClear()
    authState.user = {
      email: "user@example.com",
      full_name: "Test User",
      id: "user-1",
      is_active: true,
      is_superuser: false,
    }
  })

  test("user_menu_renders_current_user_and_settings_link", async () => {
    // Arrange
    const user = userEvent.setup()
    renderWithProviders(<UserMenu />)

    // Act
    await user.click(screen.getByTestId("user-menu"))

    // Assert
    expect(screen.getByText("Test User")).toBeVisible()
    expect(await screen.findByText("My Profile")).toBeVisible()
    expect(screen.getByRole("link", { name: /My Profile/i })).toHaveAttribute(
      "href",
      "/settings",
    )
  })

  test("user_menu_missing_name_uses_user_fallback", () => {
    // Arrange
    authState.user = {
      ...authState.user,
      full_name: "",
    }

    // Act
    renderWithProviders(<UserMenu />)

    // Assert
    expect(screen.getByText("User")).toBeVisible()
  })

  test("user_menu_logout_calls_auth_logout", async () => {
    // Arrange
    const user = userEvent.setup()
    renderWithProviders(<UserMenu />)

    // Act
    await user.click(screen.getByTestId("user-menu"))
    await user.click(await screen.findByText("Log Out"))

    // Assert
    expect(authState.logout).toHaveBeenCalled()
  })
})
