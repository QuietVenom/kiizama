import { screen } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import type { ReactNode } from "react"
import { beforeEach, describe, expect, test, vi } from "vitest"

import { renderWithProviders } from "../helpers/render"

const { authState, themeState } = vi.hoisted(() => {
  const state = {
    setTheme: vi.fn((value: string) => {
      state.theme = value
      localStorage.setItem("theme", value)
    }),
    theme: "light",
  }

  return {
    authState: {
      user: {
        id: "user-1",
        email: "user@example.com",
        full_name: "Test User",
        is_active: true,
        is_superuser: false,
      },
    },
    themeState: state,
  }
})

vi.mock("@/components/Dashboard/DashboardPageShell", () => ({
  default: ({ children }: { children: ReactNode }) => (
    <section>{children}</section>
  ),
}))

vi.mock("@/components/UserSettings/DeleteAccount", () => ({
  default: () => <div>Danger zone content</div>,
}))

vi.mock("@/components/UserSettings/Payments", () => ({
  default: () => <div>Payments content</div>,
}))

vi.mock("@/hooks/useAuth", () => ({
  default: () => authState,
}))

vi.mock("next-themes", () => ({
  ThemeProvider: ({ children }: { children: ReactNode }) => <>{children}</>,
  useTheme: () => themeState,
}))

const Appearance = (
  await import("../../../src/components/UserSettings/Appearance")
).default
const { UserSettingsPage } = await import(
  "../../../src/routes/_layout/-components/UserSettingsPage"
)

describe("appearance settings", () => {
  beforeEach(() => {
    authState.user = {
      id: "user-1",
      email: "user@example.com",
      full_name: "Test User",
      is_active: true,
      is_superuser: false,
    }
    localStorage.clear()
    themeState.theme = "light"
    themeState.setTheme.mockClear()
  })

  test("settings_tabs_normal_user_sees_all_settings_tabs", async () => {
    // Arrange / Act
    renderWithProviders(<UserSettingsPage />, { language: "en" })

    // Assert
    expect(await screen.findByRole("tab", { name: "My profile" })).toBeVisible()
    expect(await screen.findByRole("tab", { name: "Payments" })).toBeVisible()
    expect(await screen.findByRole("tab", { name: "Password" })).toBeVisible()
    expect(await screen.findByRole("tab", { name: "Appearance" })).toBeVisible()
    expect(
      await screen.findByRole("tab", { name: "Danger zone" }),
    ).toBeVisible()
  })

  test("settings_tabs_superuser_hides_payments_and_danger_zone", async () => {
    // Arrange
    authState.user = {
      ...authState.user,
      is_superuser: true,
    }

    // Act
    renderWithProviders(<UserSettingsPage />, { language: "en" })

    // Assert
    expect(await screen.findByRole("tab", { name: "My profile" })).toBeVisible()
    expect(await screen.findByRole("tab", { name: "Password" })).toBeVisible()
    expect(await screen.findByRole("tab", { name: "Appearance" })).toBeVisible()
    expect(
      screen.queryByRole("tab", { name: "Payments" }),
    ).not.toBeInTheDocument()
    expect(
      screen.queryByRole("tab", { name: "Danger zone" }),
    ).not.toBeInTheDocument()
  })

  test("appearance_theme_selection_delegates_light_dark_and_system_to_theme_provider", async () => {
    // Arrange
    const user = userEvent.setup()
    const scenarios = [
      { initialTheme: "system", label: "Dark Mode", value: "dark" },
      { initialTheme: "dark", label: "Light Mode", value: "light" },
      { initialTheme: "light", label: "System", value: "system" },
    ]

    for (const scenario of scenarios) {
      themeState.theme = scenario.initialTheme
      const { unmount } = renderWithProviders(<Appearance />, {
        language: "en",
      })

      // Act
      await user.click(screen.getByText(scenario.label))
      unmount()
    }

    // Assert
    expect(themeState.setTheme).toHaveBeenNthCalledWith(1, "dark")
    expect(themeState.setTheme).toHaveBeenNthCalledWith(2, "light")
    expect(themeState.setTheme).toHaveBeenNthCalledWith(3, "system")
    expect(localStorage.getItem("theme")).toBe("system")
  })

  test("appearance_renders_language_switcher", async () => {
    renderWithProviders(<Appearance />, { language: "en" })

    expect(await screen.findByText("Language")).toBeVisible()
    expect(
      await screen.findByRole("button", { name: "Select language" }),
    ).toBeVisible()
    expect(
      await screen.findByRole("button", { name: "Select language" }),
    ).toHaveTextContent("English")
  })
})
