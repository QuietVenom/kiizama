import { screen } from "@testing-library/react"
import { createRef, type ReactNode } from "react"
import { describe, expect, test, vi } from "vitest"

import Pricing from "../../../src/components/Landing/Pricing"
import { renderWithProviders } from "../helpers/render"

vi.mock("@tanstack/react-router", () => ({
  Link: ({ children, to }: { children: ReactNode; to: string }) => (
    <a href={to}>{children}</a>
  ),
}))

describe("landing pricing", () => {
  test("pricing_renders_current_trial_and_base_plan_packages", () => {
    // Arrange / Act
    renderWithProviders(
      <Pricing
        isWaitingListEnabled={false}
        sectionRef={createRef<HTMLElement>()}
      />,
    )

    // Assert
    expect(
      screen.getByRole("heading", {
        name: "Start free, then continue with the base monthly plan",
      }),
    ).toBeVisible()
    expect(screen.getByRole("heading", { name: "Free Trial" })).toBeVisible()
    expect(screen.getByText("$0")).toBeVisible()
    expect(screen.getByText("for 7 days")).toBeVisible()
    expect(screen.getByText("No card required")).toBeVisible()
    expect(screen.getByText("No credit or debit card to start")).toBeVisible()

    expect(screen.getByRole("heading", { name: "Base" })).toBeVisible()
    expect(screen.getByText("$389 MXN")).toBeVisible()
    expect(screen.getByText("per month (IVA included)")).toBeVisible()
    expect(screen.getByText("Monthly subscription")).toBeVisible()
    expect(
      screen.getByText("Monthly subscription in Mexican pesos"),
    ).toBeVisible()

    expect(
      screen.getAllByRole("link", { name: "Start free trial" })[0],
    ).toHaveAttribute("href", "/signup")
    expect(
      screen.getByRole("link", { name: "Start base plan" }),
    ).toHaveAttribute("href", "/signup")
  })

  test("pricing_waiting_list_mode_routes_package_ctas_to_waiting_list", () => {
    // Arrange / Act
    renderWithProviders(
      <Pricing
        isWaitingListEnabled={true}
        sectionRef={createRef<HTMLElement>()}
      />,
    )

    // Assert
    const waitingListLinks = screen.getAllByRole("link", {
      name: "Join waiting list",
    })
    expect(waitingListLinks).toHaveLength(3)
    for (const link of waitingListLinks) {
      expect(link).toHaveAttribute("href", "/waiting-list")
    }
  })
})
