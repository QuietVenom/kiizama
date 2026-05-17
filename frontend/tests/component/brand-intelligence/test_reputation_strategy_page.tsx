import { screen } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import { describe, expect, test, vi } from "vitest"

import { renderWithProviders } from "../helpers/render"

vi.mock("@/components/Dashboard/DashboardTopbar", () => ({
  default: () => <div>Dashboard topbar</div>,
}))

vi.mock(
  "@/routes/_layout/brand-intelligence/-components/CampaignStrategyTab",
  () => ({
    default: () => <section>Generate campaign strategy PDF</section>,
  }),
)

vi.mock(
  "@/routes/_layout/brand-intelligence/-components/CreatorStrategyTab",
  () => ({
    default: () => <section>Generate creator strategy PDF</section>,
  }),
)

vi.mock("@/components/BrandIntelligence/StrategyOptionCard", () => ({
  default: ({
    description,
    isActive,
    onClick,
    title,
  }: {
    description: string
    isActive: boolean
    onClick: () => void
    title: string
  }) => (
    <button aria-pressed={isActive} onClick={onClick} type="button">
      <span>{title}</span>
      <span>{description}</span>
    </button>
  ),
}))

const { ReputationStrategyPage } = await import(
  "../../../src/routes/_layout/brand-intelligence/-components/ReputationStrategyPage"
)

describe("reputation strategy page", () => {
  test("reputation_strategy_page_initial_state_renders_campaign_strategy_header_and_badges", async () => {
    // Arrange / Act
    renderWithProviders(<ReputationStrategyPage />, { language: "en" })

    // Assert
    expect(
      screen.getByRole("heading", {
        name: "Build modular reputation strategy reports.",
      }),
    ).toBeVisible()
    expect(screen.getByText("Profile validation first")).toBeVisible()
    expect(screen.getByText("PDF only")).toBeVisible()
    expect(screen.getByText("Local reports synced")).toBeVisible()
    expect(
      await screen.findByText("Generate campaign strategy PDF"),
    ).toBeVisible()
  })

  test("reputation_strategy_page_creator_strategy_selection_renders_creator_builder", async () => {
    // Arrange
    const user = userEvent.setup()
    renderWithProviders(<ReputationStrategyPage />, { language: "en" })

    // Act
    await user.click(
      screen.getByRole("button", { name: /Reputation Creator Strategy/i }),
    )

    // Assert
    expect(
      await screen.findByText("Generate creator strategy PDF"),
    ).toBeVisible()
  })
})
