import { screen } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import type { ReactNode } from "react"
import { describe, expect, test, vi } from "vitest"

import Footer from "../../../src/components/Landing/Footer"
import { renderWithProviders } from "../helpers/render"

vi.mock("@tanstack/react-router", () => ({
  Link: ({ children, to }: { children: ReactNode; to: string }) => (
    <a href={to}>{children}</a>
  ),
}))

describe("landing footer", () => {
  test("footer_renders_sections_and_cookie_settings_panel", async () => {
    const user = userEvent.setup()

    renderWithProviders(<Footer isWaitingListEnabled={false} />, {
      language: "en",
    })

    expect(screen.getByText("Product")).toBeVisible()
    expect(screen.getByText("Company")).toBeVisible()
    expect(screen.getByText("Legal")).toBeVisible()
    expect(screen.queryByRole("combobox")).not.toBeInTheDocument()

    await user.click(screen.getByRole("button", { name: "Cookie Settings" }))

    expect(await screen.findByText("Done")).toBeVisible()
    expect(screen.getByText("Accept All")).toBeVisible()
    expect(screen.getByText("Strictly Necessary")).toBeVisible()
  })
})
