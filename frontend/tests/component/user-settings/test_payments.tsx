import { screen, waitFor } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import { beforeEach, describe, expect, test, vi } from "vitest"

import type { BillingSummary } from "../../../src/features/billing/api"
import { renderWithProviders } from "../helpers/render"

const { billingApi, toast } = vi.hoisted(() => ({
  billingApi: {
    createCheckoutSession: vi.fn(),
    createPortalSession: vi.fn(),
    readBillingMe: vi.fn(),
    readBillingNotices: vi.fn(),
  },
  toast: {
    showErrorToast: vi.fn(),
    showSuccessToast: vi.fn(),
  },
}))

vi.mock("@/features/billing/api", () => {
  const billingSummaryQueryKey = ["billing", "me"] as const
  const billingNoticesQueryKey = ["billing", "notices"] as const

  return {
    billingNoticesQueryKey,
    billingNoticesQueryOptions: {
      queryFn: billingApi.readBillingNotices,
      queryKey: billingNoticesQueryKey,
      staleTime: 30_000,
    },
    billingSummaryQueryKey,
    billingSummaryQueryOptions: {
      queryFn: billingApi.readBillingMe,
      queryKey: billingSummaryQueryKey,
      staleTime: 30_000,
    },
    createCheckoutSession: billingApi.createCheckoutSession,
    createPortalSession: billingApi.createPortalSession,
    getFeatureUsage: (summary: BillingSummary | undefined, code: string) => {
      const aliases: Record<string, string[]> = {
        ig_scraper: ["ig_scraper_apify"],
      }

      return summary?.features.find(
        (feature) =>
          feature.code === code || (aliases[code] ?? []).includes(feature.code),
      )
    },
    readBillingMe: billingApi.readBillingMe,
    readBillingNotices: billingApi.readBillingNotices,
  }
})

vi.mock("@/hooks/useCustomToast", () => ({
  default: () => toast,
}))

const Payments = (await import("../../../src/components/UserSettings/Payments"))
  .default

const createBillingSummary = (
  overrides: Partial<BillingSummary> = {},
): BillingSummary => ({
  access_profile: "standard",
  access_revoked_reason: null,
  billing_eligible: true,
  cancel_at: null,
  current_period_end: null,
  current_period_start: null,
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
      limit: 2,
      name: "Social Media Reports",
      remaining: 1,
      reserved: 0,
      used: 1,
    },
    {
      code: "reputation_strategy",
      is_unlimited: true,
      limit: null,
      name: "Reputation Strategy",
      remaining: null,
      reserved: 0,
      used: 3,
    },
  ],
  latest_invoice_status: null,
  managed_access_source: null,
  notices: [],
  pending_ambassador_activation: false,
  plan_status: "none",
  renewal_day: null,
  subscription_status: null,
  trial_eligible: true,
  ...overrides,
})

describe("payments settings", () => {
  beforeEach(() => {
    billingApi.createCheckoutSession.mockReset()
    billingApi.createPortalSession.mockReset()
    billingApi.readBillingMe.mockReset()
    billingApi.readBillingNotices.mockReset()
    toast.showErrorToast.mockClear()
    toast.showSuccessToast.mockClear()
  })

  test("payments_query_loading_shows_loading_copy", async () => {
    // Arrange
    billingApi.readBillingMe.mockReturnValue(new Promise(() => undefined))

    // Act
    renderWithProviders(<Payments />)

    // Assert
    expect(await screen.findByText("Loading billing details...")).toBeVisible()
  })

  test("payments_no_plan_trial_eligible_shows_start_trial_cta", async () => {
    // Arrange
    billingApi.readBillingMe.mockResolvedValue(createBillingSummary())

    // Act
    renderWithProviders(<Payments />)

    // Assert
    expect(
      await screen.findByRole("button", { name: "Start Trial" }),
    ).toBeVisible()
    expect(screen.getByText("None")).toBeVisible()
  })

  test("payments_no_plan_without_trial_shows_start_base_plan_cta", async () => {
    // Arrange
    billingApi.readBillingMe.mockResolvedValue(
      createBillingSummary({ trial_eligible: false }),
    )

    // Act
    renderWithProviders(<Payments />)

    // Assert
    expect(
      await screen.findByRole("button", { name: "Start Base Plan" }),
    ).toBeVisible()
  })

  test("payments_active_plan_shows_manage_billing_cta", async () => {
    // Arrange
    billingApi.readBillingMe.mockResolvedValue(
      createBillingSummary({
        plan_status: "base",
        renewal_day: "2026-02-15",
        subscription_status: "active",
      }),
    )

    // Act
    renderWithProviders(<Payments />)

    // Assert
    expect(await screen.findByText("Base")).toBeVisible()
    expect(screen.getByText("Active")).toBeVisible()
    expect(screen.getByRole("button", { name: "Manage Billing" })).toBeVisible()
    expect(
      screen.queryByRole("button", { name: "Start Trial" }),
    ).not.toBeInTheDocument()
  })

  test("payments_paused_subscription_shows_add_payment_method_cta", async () => {
    // Arrange
    billingApi.readBillingMe.mockResolvedValue(
      createBillingSummary({
        plan_status: "base",
        subscription_status: "paused",
      }),
    )

    // Act
    renderWithProviders(<Payments />)

    // Assert
    expect(
      await screen.findByRole("button", { name: "Add Payment Method" }),
    ).toBeVisible()
  })

  test("payments_managed_access_hides_checkout_and_portal_ctas", async () => {
    // Arrange
    billingApi.readBillingMe.mockResolvedValue(
      createBillingSummary({
        access_profile: "ambassador",
        managed_access_source: "admin",
        plan_status: "base",
        subscription_status: "active",
      }),
    )

    // Act
    renderWithProviders(<Payments />)

    // Assert
    expect(await screen.findByText("Admin")).toBeVisible()
    expect(
      screen.queryByRole("button", { name: "Start Trial" }),
    ).not.toBeInTheDocument()
    expect(
      screen.queryByRole("button", { name: "Manage Billing" }),
    ).not.toBeInTheDocument()
  })

  test("payments_checkout_error_shows_error_toast", async () => {
    // Arrange
    const user = userEvent.setup()
    billingApi.readBillingMe.mockResolvedValue(createBillingSummary())
    billingApi.createCheckoutSession.mockRejectedValue(
      new Error("Checkout unavailable"),
    )
    renderWithProviders(<Payments />)

    // Act
    await user.click(await screen.findByRole("button", { name: "Start Trial" }))

    // Assert
    await waitFor(() => {
      expect(billingApi.createCheckoutSession).toHaveBeenCalledTimes(1)
      expect(toast.showErrorToast).toHaveBeenCalledWith("Checkout unavailable")
    })
  })

  test("payments_portal_error_shows_error_toast", async () => {
    // Arrange
    const user = userEvent.setup()
    billingApi.readBillingMe.mockResolvedValue(
      createBillingSummary({
        plan_status: "base",
        subscription_status: "active",
      }),
    )
    billingApi.createPortalSession.mockRejectedValue(
      new Error("Portal unavailable"),
    )
    renderWithProviders(<Payments />)

    // Act
    await user.click(
      await screen.findByRole("button", { name: "Manage Billing" }),
    )

    // Assert
    await waitFor(() => {
      expect(billingApi.createPortalSession).toHaveBeenCalledTimes(1)
      expect(toast.showErrorToast).toHaveBeenCalledWith("Portal unavailable")
    })
  })

  test("payments_notices_available_renders_notice_status_and_message", async () => {
    // Arrange
    billingApi.readBillingMe.mockResolvedValue(
      createBillingSummary({
        notices: [
          {
            created_at: "2026-01-01T00:00:00Z",
            effective_at: null,
            expires_at: null,
            id: "notice-1",
            message: "Your invoice will be charged soon.",
            notice_type: "invoice_upcoming",
            status: "unread",
            title: "Upcoming invoice",
          },
        ],
      }),
    )

    // Act
    renderWithProviders(<Payments />)

    // Assert
    expect(await screen.findByText("Billing notices")).toBeVisible()
    expect(screen.getByText("Upcoming invoice")).toBeVisible()
    expect(screen.getByText("unread")).toBeVisible()
    expect(screen.getByText("Your invoice will be charged soon.")).toBeVisible()
  })
})
