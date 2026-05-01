import { screen, waitFor } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import { beforeEach, describe, expect, test, vi } from "vitest"

import type { BillingNotice } from "../../../src/features/billing/api"
import { renderWithProviders } from "../helpers/render"

const { billingApi } = vi.hoisted(() => ({
  billingApi: {
    dismissBillingNotice: vi.fn(),
    markBillingNoticeRead: vi.fn(),
    readBillingNotices: vi.fn(),
  },
}))

vi.mock("@/features/billing/api", () => {
  const billingNoticesQueryKey = ["billing", "notices"] as const
  const billingSummaryQueryKey = ["billing", "me"] as const

  return {
    billingNoticesQueryKey,
    billingSummaryQueryKey,
    dismissBillingNotice: billingApi.dismissBillingNotice,
    markBillingNoticeRead: billingApi.markBillingNoticeRead,
    readBillingNotices: billingApi.readBillingNotices,
  }
})

const DashboardTopbar = (
  await import("../../../src/components/Dashboard/DashboardTopbar")
).default

const createBillingNotice = (
  overrides: Partial<BillingNotice> = {},
): BillingNotice => ({
  created_at: "2026-01-01T00:00:00Z",
  effective_at: null,
  expires_at: null,
  id: "notice-1",
  message: "A billing notice message.",
  notice_type: "trial_will_end",
  status: "unread",
  title: "Trial ending",
  ...overrides,
})

describe("dashboard billing notices", () => {
  beforeEach(() => {
    billingApi.dismissBillingNotice.mockReset()
    billingApi.markBillingNoticeRead.mockReset()
    billingApi.readBillingNotices.mockReset()
  })

  test("billing_notices_empty_collection_renders_fallback_copy", async () => {
    // Arrange
    const user = userEvent.setup()
    billingApi.readBillingNotices.mockResolvedValue({ data: [] })
    renderWithProviders(<DashboardTopbar />)

    // Act
    await user.click(
      await screen.findByRole("button", { name: "Billing notices" }),
    )

    // Assert
    expect(await screen.findByText("No billing notices")).toBeVisible()
    expect(
      screen.getByText(
        "Upcoming renewals and trial reminders will appear here.",
      ),
    ).toBeVisible()
  })

  test("billing_notices_unread_count_badge_counts_unread_notices_only", async () => {
    // Arrange
    const user = userEvent.setup()
    billingApi.readBillingNotices.mockResolvedValue({
      data: [
        createBillingNotice({ id: "notice-1", status: "unread" }),
        createBillingNotice({
          id: "notice-2",
          status: "read",
          title: "Read notice",
        }),
        createBillingNotice({
          id: "notice-3",
          status: "unread",
          title: "Second unread notice",
        }),
      ],
    })
    renderWithProviders(<DashboardTopbar />)

    // Act
    await user.click(
      await screen.findByRole("button", { name: "Billing notices" }),
    )

    // Assert
    expect(await screen.findByText("Trial ending")).toBeVisible()
    expect(screen.getByText("Second unread notice")).toBeVisible()
    expect(screen.getByText("2")).toBeVisible()
  })

  test("billing_notices_mark_as_read_calls_api_and_invalidates_billing_queries", async () => {
    // Arrange
    const user = userEvent.setup()
    billingApi.readBillingNotices.mockResolvedValue({
      data: [createBillingNotice({ id: "notice-read" })],
    })
    billingApi.markBillingNoticeRead.mockResolvedValue(
      createBillingNotice({ id: "notice-read", status: "read" }),
    )
    const { queryClient } = renderWithProviders(<DashboardTopbar />)
    const invalidateQueries = vi.spyOn(queryClient, "invalidateQueries")

    // Act
    await user.click(
      await screen.findByRole("button", { name: "Billing notices" }),
    )
    await user.click(
      await screen.findByRole("button", { name: "Mark as read" }),
    )

    // Assert
    await waitFor(() => {
      expect(billingApi.markBillingNoticeRead).toHaveBeenCalledWith(
        "notice-read",
      )
      expect(invalidateQueries).toHaveBeenCalledWith({
        queryKey: ["billing", "notices"],
      })
      expect(invalidateQueries).toHaveBeenCalledWith({
        queryKey: ["billing", "me"],
      })
    })
  })

  test("billing_notices_dismiss_calls_api_and_invalidates_billing_queries", async () => {
    // Arrange
    const user = userEvent.setup()
    billingApi.readBillingNotices.mockResolvedValue({
      data: [createBillingNotice({ id: "notice-dismiss", status: "read" })],
    })
    billingApi.dismissBillingNotice.mockResolvedValue(
      createBillingNotice({ id: "notice-dismiss", status: "dismissed" }),
    )
    const { queryClient } = renderWithProviders(<DashboardTopbar />)
    const invalidateQueries = vi.spyOn(queryClient, "invalidateQueries")

    // Act
    await user.click(
      await screen.findByRole("button", { name: "Billing notices" }),
    )
    await user.click(await screen.findByRole("button", { name: "Dismiss" }))

    // Assert
    await waitFor(() => {
      expect(billingApi.dismissBillingNotice).toHaveBeenCalledWith(
        "notice-dismiss",
      )
      expect(invalidateQueries).toHaveBeenCalledWith({
        queryKey: ["billing", "notices"],
      })
      expect(invalidateQueries).toHaveBeenCalledWith({
        queryKey: ["billing", "me"],
      })
    })
  })
})
