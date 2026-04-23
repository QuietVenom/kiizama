import { screen, waitFor } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import type { ReactNode } from "react"
import { beforeEach, describe, expect, test, vi } from "vitest"

import { renderWithProviders } from "../helpers/render"

const authState = {
  error: null as string | null,
  resetError: vi.fn(),
  loginMutation: {
    mutateAsync: vi.fn(),
  },
}

vi.mock("@tanstack/react-router", () => ({
  createFileRoute: () => (config: unknown) => config,
  Link: ({
    children,
    to,
    className,
  }: {
    children: ReactNode
    to: string
    className?: string
  }) => (
    <a className={className} href={to}>
      {children}
    </a>
  ),
  redirect: vi.fn(),
}))

vi.mock("@/hooks/useAuth", () => ({
  default: () => authState,
}))

vi.mock("@/components/Common/ThemeLogo", () => ({
  default: () => <span>Kiizama</span>,
}))

const { LoginPage } = await import("../../../src/routes/-components/LoginPage")

describe("login form", () => {
  beforeEach(() => {
    authState.error = null
    authState.resetError.mockClear()
    authState.loginMutation.mutateAsync.mockReset()
  })

  test("login_form_initial_state_renders_fields_and_links", () => {
    // Arrange / Act
    renderWithProviders(<LoginPage />)

    // Assert
    expect(screen.getByPlaceholderText("Email")).toBeVisible()
    expect(screen.getByPlaceholderText("Password")).toBeVisible()
    expect(
      screen.getByRole("link", { name: "Forgot Password?" }),
    ).toHaveAttribute("href", "/recover-password")
    expect(screen.getByRole("link", { name: "Sign Up" })).toHaveAttribute(
      "href",
      "/signup",
    )
  })

  test("login_form_invalid_email_shows_validation_error_without_submitting", async () => {
    // Arrange
    const user = userEvent.setup()
    renderWithProviders(<LoginPage />)

    // Act
    await user.type(screen.getByPlaceholderText("Email"), "not-an-email")
    await user.click(screen.getByRole("button", { name: "Log In" }))

    // Assert
    expect(await screen.findByText("Invalid email address")).toBeVisible()
    expect(authState.loginMutation.mutateAsync).not.toHaveBeenCalled()
  })

  test("login_form_missing_credentials_show_required_validation_errors", async () => {
    // Arrange
    const user = userEvent.setup()
    renderWithProviders(<LoginPage />)

    // Act
    await user.click(screen.getByRole("button", { name: "Log In" }))

    // Assert
    expect(await screen.findByText("Username is required")).toBeVisible()
    expect(await screen.findByText("Password is required")).toBeVisible()
    expect(authState.loginMutation.mutateAsync).not.toHaveBeenCalled()
  })

  test("login_form_backend_401_error_renders_user_facing_error", () => {
    // Arrange
    authState.error = "Incorrect email or password"

    // Act
    renderWithProviders(<LoginPage />)

    // Assert
    expect(screen.getByText("Incorrect email or password")).toBeVisible()
  })

  test("login_form_valid_submit_resets_error_and_calls_login", async () => {
    // Arrange
    const user = userEvent.setup()
    authState.loginMutation.mutateAsync.mockResolvedValue(undefined)
    renderWithProviders(<LoginPage />)

    // Act
    await user.type(screen.getByPlaceholderText("Email"), "user@example.com")
    await user.type(screen.getByPlaceholderText("Password"), "secret-password")
    await user.click(screen.getByRole("button", { name: "Log In" }))

    // Assert
    await waitFor(() => {
      expect(authState.loginMutation.mutateAsync).toHaveBeenCalledWith({
        username: "user@example.com",
        password: "secret-password",
      })
    })
    expect(authState.resetError).toHaveBeenCalled()
  })
})
