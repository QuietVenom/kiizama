import { expect, type Page, test } from "@playwright/test"

import { anonymousStorageState } from "./utils/storageState"

const mockAuthenticatedSession = async (page: Page) => {
  await page.addInitScript(() => {
    localStorage.setItem("access_token", "test-token")
  })
}

const mockUserEventsStream = async (page: Page) => {
  await page.route("**/api/v1/events/stream", async (route) => {
    await route.fulfill({
      status: 403,
      contentType: "text/event-stream",
      body: "",
    })
  })
}

test.describe("Billing return refetch", () => {
  test.use({
    storageState: anonymousStorageState,
  })

  test("refetches billing summary and notices when returning from Stripe", async ({
    page,
  }) => {
    await mockAuthenticatedSession(page)
    await mockUserEventsStream(page)

    let billingSummaryRequests = 0
    let billingNoticeRequests = 0

    await page.route("**/api/v1/users/**", async (route) => {
      const url = new URL(route.request().url())

      if (url.pathname === "/api/v1/users/me") {
        await route.fulfill({
          status: 200,
          contentType: "application/json",
          body: JSON.stringify({
            id: "user_123",
            email: "user@example.com",
            full_name: "Normal User",
            is_active: true,
            is_superuser: false,
          }),
        })
        return
      }

      await route.continue()
    })

    await page.route("**/api/v1/billing/me", async (route) => {
      billingSummaryRequests += 1
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          access_profile: "standard",
          managed_access_source: null,
          billing_eligible: true,
          trial_eligible: true,
          plan_status: "none",
          subscription_status: null,
          latest_invoice_status: null,
          access_revoked_reason: null,
          pending_ambassador_activation: false,
          cancel_at: null,
          current_period_start: null,
          current_period_end: null,
          renewal_day: null,
          features: [
            {
              code: "ig_scraper",
              name: "Profiles",
              limit: 0,
              used: 0,
              reserved: 0,
              remaining: 0,
              is_unlimited: false,
            },
            {
              code: "social_media_report",
              name: "Social Media Reports",
              limit: 0,
              used: 0,
              reserved: 0,
              remaining: 0,
              is_unlimited: false,
            },
            {
              code: "reputation_strategy",
              name: "Reputation Strategy",
              limit: 0,
              used: 0,
              reserved: 0,
              remaining: 0,
              is_unlimited: false,
            },
          ],
          notices: [],
        }),
      })
    })

    await page.route("**/api/v1/billing/notices", async (route) => {
      billingNoticeRequests += 1
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({ data: [] }),
      })
    })

    await page.goto("/settings?tab=payments&billing_return=1")

    await expect(page.getByRole("heading", { name: "Payments" })).toBeVisible()
    await expect.poll(() => billingSummaryRequests).toBeGreaterThanOrEqual(2)
    await expect.poll(() => billingNoticeRequests).toBeGreaterThanOrEqual(2)
    await expect(page).not.toHaveURL(/billing_return=/)
  })
})
