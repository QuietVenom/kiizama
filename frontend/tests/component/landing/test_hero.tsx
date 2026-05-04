import { screen } from "@testing-library/react"
import { createRef, type ReactNode } from "react"
import { describe, expect, test, vi } from "vitest"

import Hero from "../../../src/components/Landing/Hero"
import { renderWithProviders } from "../helpers/render"

vi.mock("@tanstack/react-router", () => ({
  Link: ({ children, to }: { children: ReactNode; to: string }) => (
    <a href={to}>{children}</a>
  ),
}))

describe("landing hero", () => {
  test("hero_renders_primary_value_prop_and_waiting_list_cta", () => {
    renderWithProviders(
      <Hero
        isWaitingListEnabled={true}
        sectionRef={createRef<HTMLElement>()}
      />,
      { language: "en" },
    )

    expect(screen.getByText("Instagram Reputation Intelligence")).toBeVisible()
    expect(
      screen.getByRole("heading", {
        name: /Turn social media data into reputation strategy/i,
      }),
    ).toBeVisible()
    expect(
      screen.getByRole("link", { name: /Join waiting list/i }),
    ).toHaveAttribute("href", "/waiting-list")
    expect(screen.getByText("Creator Performance Report")).toBeVisible()
  })

  test("hero_uses_translated_signup_cta_when_waiting_list_is_disabled", () => {
    renderWithProviders(
      <Hero
        isWaitingListEnabled={false}
        sectionRef={createRef<HTMLElement>()}
      />,
      { language: "es" },
    )

    expect(screen.getByRole("link", { name: /Crear cuenta/i })).toHaveAttribute(
      "href",
      "/signup",
    )
  })
})
