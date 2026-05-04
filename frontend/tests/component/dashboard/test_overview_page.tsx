import { screen } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import { beforeEach, describe, expect, test, vi } from "vitest"

import {
  type BillingSummary,
  billingSummaryQueryKey,
} from "../../../src/features/billing/api"
import { createTestQueryClient, renderWithProviders } from "../helpers/render"

const { authState, router } = vi.hoisted(() => ({
  authState: {
    user: {
      email: "marcos@example.com",
      full_name: "Marcos",
    },
  },
  router: {
    navigate: vi.fn(),
  },
}))

vi.mock("@tanstack/react-router", () => ({
  useNavigate: () => router.navigate,
}))

vi.mock("@/hooks/useAuth", () => ({
  default: () => authState,
}))

vi.mock("@/components/Dashboard/DashboardTopbar", () => ({
  default: () => <div>Dashboard topbar</div>,
}))

vi.mock("@/components/Dashboard/RecentReportsCard", () => ({
  default: () => <section>Recent reports</section>,
}))

const { OverviewPage } = await import(
  "../../../src/routes/_layout/-components/OverviewPage"
)

const createBillingSummary = (
  overrides: Partial<BillingSummary> = {},
): BillingSummary => ({
  access_profile: "standard",
  access_revoked_reason: null,
  billing_eligible: true,
  cancel_at: null,
  current_period_end: "2026-05-01",
  current_period_start: "2026-04-01",
  features: [
    {
      code: "ig_scraper",
      is_unlimited: false,
      limit: 10,
      name: "Profiles",
      remaining: 8,
      reserved: 0,
      used: 2,
    },
    {
      code: "social_media_report",
      is_unlimited: false,
      limit: 5,
      name: "Reports",
      remaining: 4,
      reserved: 0,
      used: 1,
    },
    {
      code: "reputation_strategy",
      is_unlimited: false,
      limit: 3,
      name: "Reputation",
      remaining: 2,
      reserved: 0,
      used: 1,
    },
  ],
  latest_invoice_status: null,
  managed_access_source: null,
  notices: [],
  pending_ambassador_activation: false,
  plan_status: "base",
  renewal_day: "2026-05-01",
  subscription_status: "active",
  trial_eligible: false,
  ...overrides,
})

const renderOverviewPage = (billing: BillingSummary) => {
  const queryClient = createTestQueryClient()
  queryClient.setQueryData(billingSummaryQueryKey, billing)
  return renderWithProviders(<OverviewPage />, { queryClient })
}

describe("overview page", () => {
  beforeEach(() => {
    router.navigate.mockClear()
    authState.user = {
      email: "marcos@example.com",
      full_name: "Marcos",
    }
  })

  test("overview_page_with_user_and_billing_summary_renders_greeting_and_credits", () => {
    // Arrange / Act
    renderOverviewPage(createBillingSummary())

    // Assert
    expect(screen.getByText(/Hola, Marcos/)).toBeVisible()
    expect(screen.getByText("Perfiles")).toBeVisible()
    expect(screen.getAllByText("créditos actuales")).toHaveLength(3)
    expect(screen.getByText("Reportes de social media")).toBeVisible()
    expect(screen.getByText("Estrategia reputacional")).toBeVisible()
    expect(screen.getByText("8 / 10")).toBeVisible()
    expect(screen.getByText("4 / 5")).toBeVisible()
    expect(screen.getByText("2 / 3")).toBeVisible()
  })

  test("overview_page_active_plan_payments_cta_navigates_to_payments_settings", async () => {
    // Arrange
    const user = userEvent.setup()
    renderOverviewPage(createBillingSummary())

    // Act
    await user.click(screen.getByRole("button", { name: "Pagos" }))

    // Assert
    expect(router.navigate).toHaveBeenCalledWith({
      search: { tab: "payments" },
      to: "/settings",
    })
  })

  test("overview_page_without_plan_activation_cta_navigates_to_payments_settings", async () => {
    // Arrange
    const user = userEvent.setup()
    renderOverviewPage(createBillingSummary({ plan_status: "none" }))

    // Act
    await user.click(
      screen.getByRole("button", { name: "Activa tu suscripción" }),
    )

    // Assert
    expect(router.navigate).toHaveBeenCalledWith({
      search: { tab: "payments" },
      to: "/settings",
    })
  })

  test("overview_page_managed_access_hides_payments_cta", () => {
    // Arrange / Act
    renderOverviewPage(
      createBillingSummary({
        managed_access_source: "admin",
      }),
    )

    // Assert
    expect(
      screen.queryByRole("button", { name: "Pagos" }),
    ).not.toBeInTheDocument()
    expect(
      screen.queryByRole("button", { name: "Activa tu suscripción" }),
    ).not.toBeInTheDocument()
  })
})
