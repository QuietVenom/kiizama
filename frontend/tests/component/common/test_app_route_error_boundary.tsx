import { screen, waitFor } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import type { ReactNode } from "react"
import { beforeEach, describe, expect, test, vi } from "vitest"

import { ApiError } from "../../../src/client/core/ApiError"
import AppRouteErrorBoundary from "../../../src/components/Common/AppRouteErrorBoundary"
import { renderWithProviders } from "../helpers/render"

const { redirectToLoginWithReturnTo, router } = vi.hoisted(() => ({
  redirectToLoginWithReturnTo: vi.fn(),
  router: {
    latestLocation: {
      href: "/settings?tab=profile",
    },
    invalidate: vi.fn(),
  },
}))

vi.mock("@tanstack/react-router", () => ({
  useRouter: () => router,
  isNotFound: () => false,
  Link: ({ children, to }: { children: ReactNode; to: string }) => (
    <a href={to}>{children}</a>
  ),
}))

vi.mock("@/features/errors/navigation", async (importOriginal) => {
  const actual =
    await importOriginal<typeof import("@/features/errors/navigation")>()
  return {
    ...actual,
    redirectToLoginWithReturnTo,
  }
})

const createApiError = (status: number, detail?: string) =>
  new ApiError(
    {
      method: "GET",
      url: "/api/test",
    } as never,
    {
      body: detail ? { detail } : undefined,
      ok: false,
      status,
      statusText: "Error",
      url: "/api/test",
    },
    detail || "Error",
  )

describe("app route error boundary", () => {
  beforeEach(() => {
    router.invalidate.mockClear()
    redirectToLoginWithReturnTo.mockClear()
  })

  test("route_error_boundary_401_redirects_to_login_and_clears_screen", async () => {
    // Arrange / Act
    renderWithProviders(
      <AppRouteErrorBoundary
        error={createApiError(401)}
        info={{ componentStack: "" }}
        reset={vi.fn()}
      />,
    )

    // Assert
    await waitFor(() => {
      expect(redirectToLoginWithReturnTo).toHaveBeenCalledWith(
        "/settings?tab=profile",
      )
    })
    expect(screen.queryByText("401")).not.toBeInTheDocument()
  })

  test("route_error_boundary_403_renders_forbidden_screen", () => {
    // Arrange / Act
    renderWithProviders(
      <AppRouteErrorBoundary
        error={createApiError(403)}
        info={{ componentStack: "" }}
        reset={vi.fn()}
      />,
    )

    // Assert
    expect(screen.getByTestId("forbidden")).toBeVisible()
    expect(screen.getByText("403")).toBeVisible()
  })

  test("route_error_boundary_503_retry_resets_and_invalidates_router", async () => {
    // Arrange
    const user = userEvent.setup()
    const reset = vi.fn()
    renderWithProviders(
      <AppRouteErrorBoundary
        error={createApiError(503, "OpenAI is unavailable")}
        info={{ componentStack: "" }}
        reset={reset}
      />,
    )

    // Act
    await user.click(screen.getByRole("button", { name: "Try Again" }))

    // Assert
    expect(screen.getByText("503")).toBeVisible()
    expect(reset).toHaveBeenCalledOnce()
    expect(router.invalidate).toHaveBeenCalledOnce()
  })

  test("route_error_boundary_unknown_error_renders_server_error", () => {
    // Arrange / Act
    renderWithProviders(
      <AppRouteErrorBoundary
        error={new Error("Unexpected failure")}
        info={{ componentStack: "" }}
        reset={vi.fn()}
      />,
    )

    // Assert
    expect(screen.getByTestId("server-error")).toBeVisible()
    expect(screen.getByText("500")).toBeVisible()
    expect(screen.getByText("Unexpected failure")).toBeVisible()
  })
})
