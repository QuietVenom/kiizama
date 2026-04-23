import { screen } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import type { ReactNode } from "react"
import { beforeEach, describe, expect, test, vi } from "vitest"

import { renderWithProviders } from "../helpers/render"

const { authState, routeState } = vi.hoisted(() => ({
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
  routeState: {
    pathname: "/overview",
  },
}))

vi.mock("@/hooks/useAuth", () => ({
  default: () => authState,
}))

vi.mock("@/components/Common/ThemeLogo", () => ({
  default: () => <span>Kiizama</span>,
}))

vi.mock("@tanstack/react-router", () => ({
  Link: ({
    children,
    onClick,
    to,
  }: {
    children: ReactNode
    onClick?: () => void
    to: string
  }) => (
    <a href={to} onClick={onClick}>
      {children}
    </a>
  ),
  useLocation: () => ({ pathname: routeState.pathname }),
}))

const Sidebar = (await import("../../../src/components/Common/Sidebar")).default

describe("sidebar navigation", () => {
  beforeEach(() => {
    authState.logout.mockClear()
    authState.user = {
      email: "user@example.com",
      full_name: "Test User",
      id: "user-1",
      is_active: true,
      is_superuser: false,
    }
    routeState.pathname = "/overview"
  })

  test("sidebar_regular_user_renders_primary_routes_and_hides_admin", () => {
    // Arrange / Act
    renderWithProviders(<Sidebar />)

    // Assert
    expect(screen.getAllByText("Overview").length).toBeGreaterThan(0)
    expect(screen.getAllByText("Creators Search").length).toBeGreaterThan(0)
    expect(screen.getAllByText("Brand Intelligence").length).toBeGreaterThan(0)
    expect(screen.getAllByText("Settings").length).toBeGreaterThan(0)
    expect(screen.queryByText("Admin")).not.toBeInTheDocument()
    expect(screen.getAllByText("Test User").length).toBeGreaterThan(0)
    expect(screen.getAllByText("user@example.com").length).toBeGreaterThan(0)
  })

  test("sidebar_superuser_renders_admin_and_plan_label", () => {
    // Arrange
    authState.user = {
      ...authState.user,
      is_superuser: true,
    }

    // Act
    renderWithProviders(<Sidebar />)

    // Assert
    expect(screen.getAllByText("Admin").length).toBeGreaterThan(0)
    expect(screen.getAllByText("Admin Plan").length).toBeGreaterThan(0)
  })

  test("sidebar_brand_intelligence_child_route_expands_section", () => {
    // Arrange
    routeState.pathname = "/brand-intelligence/reputation-strategy"

    // Act
    renderWithProviders(<Sidebar />)

    // Assert
    expect(screen.getAllByText("Reputation Strategy").length).toBeGreaterThan(0)
  })

  test("sidebar_logout_calls_auth_logout", async () => {
    // Arrange
    const user = userEvent.setup()
    renderWithProviders(<Sidebar />)

    // Act
    await user.click(screen.getAllByText("Log Out")[0])

    // Assert
    expect(authState.logout).toHaveBeenCalled()
  })

  test("sidebar_mobile_menu_button_opens_drawer_navigation", async () => {
    // Arrange
    const user = userEvent.setup()
    renderWithProviders(<Sidebar />)

    // Act
    await user.click(screen.getByRole("button", { name: "Open menu" }))

    // Assert
    expect(screen.getAllByText("Overview").length).toBeGreaterThan(1)
  })
})
