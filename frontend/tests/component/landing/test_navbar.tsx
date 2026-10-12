import { screen } from "@testing-library/react"
import { createRef, type ReactNode } from "react"
import { describe, expect, test, vi } from "vitest"

import LandingNavbar from "../../../src/components/Landing/Navbar"
import { renderWithProviders } from "../helpers/render"

vi.mock("@/components/Common/ThemeLogo", () => ({
  default: () => <span>Kiizama</span>,
}))

vi.mock("@tanstack/react-router", () => ({
  Link: ({ children, to }: { children: ReactNode; to: string }) => (
    <a href={to}>{children}</a>
  ),
}))

describe("landing navbar", () => {
  test("landing_navbar_renders_language_switcher", () => {
    renderWithProviders(
      <LandingNavbar
        isWaitingListEnabled={false}
        navbarRef={createRef<HTMLElement>()}
      />,
      { language: "en" },
    )

    expect(
      screen.getAllByRole("button", { name: "Select language" }).length,
    ).toBeGreaterThan(0)
    expect(screen.getAllByText("English").length).toBeGreaterThan(0)
  })

  test("landing_navbar_blog_links_request_the_current_blog_document", () => {
    renderWithProviders(
      <LandingNavbar
        isWaitingListEnabled={false}
        navbarRef={createRef<HTMLElement>()}
      />,
      { language: "en" },
    )

    const blogLinks = screen.getAllByRole("link", { name: "Blog" })
    expect(blogLinks.length).toBeGreaterThan(0)
    for (const link of blogLinks) {
      expect(link).toHaveAttribute("href", "/blog")
    }
  })
})
