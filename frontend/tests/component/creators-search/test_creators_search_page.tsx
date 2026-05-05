import { screen } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import { describe, expect, test, vi } from "vitest"

import { renderWithProviders } from "../helpers/render"

vi.mock("@/components/Dashboard/DashboardTopbar", () => ({
  default: () => <div>Dashboard topbar</div>,
}))

vi.mock(
  "@/routes/_layout/-components/creators-search/DirectCreatorsSearchTab",
  () => ({
    default: () => <section>Direct creators search content</section>,
  }),
)

vi.mock(
  "@/routes/_layout/-components/creators-search/SearchGuideDialog",
  () => ({
    SearchGuideDialog: ({ open }: { open: boolean }) =>
      open ? <div>Search guide dialog</div> : null,
  }),
)

const { CreatorsSearchPage } = await import(
  "../../../src/routes/_layout/-components/creators-search/CreatorsSearchPage"
)

describe("creators search page", () => {
  test("creators_search_page_initial_state_renders_direct_search_tab", async () => {
    // Arrange / Act
    renderWithProviders(<CreatorsSearchPage />, { language: "en" })

    // Assert
    expect(
      screen.getByRole("heading", {
        name: "Search saved creator profiles in one request.",
      }),
    ).toBeVisible()
    expect(screen.getByText("Direct Creator Search")).toBeVisible()
    expect(screen.getByText("Browse by Category or Role")).toBeVisible()
    expect(
      await screen.findByText("Direct creators search content"),
    ).toBeVisible()
  })

  test("creators_search_page_directory_tab_selection_renders_directory_preview", async () => {
    // Arrange
    const user = userEvent.setup()
    renderWithProviders(<CreatorsSearchPage />, { language: "en" })

    // Act
    await user.click(
      screen.getByRole("tab", { name: /Browse by Category or Role/i }),
    )

    // Assert
    expect(
      await screen.findByText("Run a search to explore saved creators."),
    ).toBeVisible()
  })
})
