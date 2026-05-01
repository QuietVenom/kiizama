import { screen } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import type { ReactNode } from "react"
import { describe, expect, test, vi } from "vitest"

import HttpErrorScreen from "../../../src/components/Common/HttpErrorScreen"
import { renderWithProviders } from "../helpers/render"

vi.mock("@tanstack/react-router", () => ({
  Link: ({ children, to }: { children: ReactNode; to: string }) => (
    <a href={to}>{children}</a>
  ),
}))

describe("HTTP error screen", () => {
  test("http_error_screen_forbidden_renders_copy_and_navigation_actions", () => {
    // Arrange / Act
    renderWithProviders(
      <HttpErrorScreen
        dataTestId="forbidden-screen"
        message="You do not have permission."
        primaryActionHref="/overview"
        primaryActionLabel="Go home"
        secondaryActionHref="/login"
        secondaryActionLabel="Log in again"
        statusCode={403}
        title="Access denied"
      />,
    )

    // Assert
    expect(screen.getByTestId("forbidden-screen")).toBeVisible()
    expect(screen.getByText("403")).toBeVisible()
    expect(screen.getByText("Access denied")).toBeVisible()
    expect(screen.getByText("You do not have permission.")).toBeVisible()
    expect(screen.getByRole("link", { name: "Go home" })).toHaveAttribute(
      "href",
      "/overview",
    )
    expect(screen.getByRole("link", { name: "Log in again" })).toHaveAttribute(
      "href",
      "/login",
    )
  })

  test("http_error_screen_retry_action_calls_handler", async () => {
    // Arrange
    const user = userEvent.setup()
    const onRetry = vi.fn()
    renderWithProviders(
      <HttpErrorScreen
        dataTestId="server-error-screen"
        message="Try again later."
        onPrimaryAction={onRetry}
        primaryActionLabel="Retry"
        statusCode={500}
        title="Something went wrong"
      />,
    )

    // Act
    await user.click(screen.getByRole("button", { name: "Retry" }))

    // Assert
    expect(onRetry).toHaveBeenCalledOnce()
  })

  test("http_error_screen_service_unavailable_renders_503_state", () => {
    // Arrange / Act
    renderWithProviders(
      <HttpErrorScreen
        dataTestId="service-unavailable-screen"
        message="Service is unavailable."
        statusCode={503}
        title="Service unavailable"
      />,
    )

    // Assert
    expect(screen.getByTestId("service-unavailable-screen")).toBeVisible()
    expect(screen.getByText("503")).toBeVisible()
    expect(screen.getByText("Service unavailable")).toBeVisible()
  })
})
