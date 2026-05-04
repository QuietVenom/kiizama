import { expect, type Page, type Route, test } from "@playwright/test"

import { anonymousStorageState } from "./utils/storageState"

const jobId = "job_mocked_123"
const requestedUsername = "missing_creator"
const readyUsername = "ready_creator"

const mockAuthenticatedSession = async (page: Page) => {
  await page.addInitScript(() => {
    localStorage.setItem("access_token", "test-token")
  })
}

const fulfillJson = async (route: Route, body: unknown, status = 200) => {
  await route.fulfill({
    status,
    contentType: "application/json",
    body: JSON.stringify(body),
  })
}

const mockAppShellApis = async (page: Page) => {
  await page.route("**/api/v1/users/**", async (route) => {
    const url = new URL(route.request().url())

    if (url.pathname === "/api/v1/users/me") {
      await fulfillJson(route, {
        id: "user_123",
        email: "user@example.com",
        full_name: "Normal User",
        is_active: true,
        is_superuser: false,
      })
      return
    }

    await route.continue()
  })

  await page.route("**/api/v1/billing/me", async (route) => {
    await fulfillJson(route, {
      access_profile: "standard",
      managed_access_source: null,
      billing_eligible: true,
      trial_eligible: false,
      plan_status: "base",
      subscription_status: "active",
      latest_invoice_status: null,
      access_revoked_reason: null,
      pending_ambassador_activation: false,
      cancel_at: null,
      current_period_start: "2026-04-01",
      current_period_end: "2026-05-01",
      renewal_day: 1,
      features: [
        {
          code: "ig_scraper",
          name: "Profiles",
          limit: 50,
          used: 0,
          reserved: 0,
          remaining: 50,
          is_unlimited: false,
        },
      ],
      notices: [],
    })
  })

  await page.route("**/api/v1/billing/notices", async (route) => {
    await fulfillJson(route, { data: [] })
  })

  await page.route("**/api/v1/events/stream", async (route) => {
    await route.fulfill({
      status: 403,
      contentType: "text/event-stream",
      body: "",
    })
  })

  await page.route("**/api/v1/creators-search/history**", async (route) => {
    if (route.request().method() === "GET") {
      await fulfillJson(route, { items: [], count: 0 })
      return
    }

    await fulfillJson(route, {
      id: "history_123",
      created_at: "2026-04-25T00:00:00Z",
      source: "ig-scrape-job",
      job_id: jobId,
      ready_usernames: [readyUsername],
    })
  })
}

const mockCreatorsSearchApis = async (page: Page) => {
  await page.route(
    "**/api/v1/ig-profile-snapshots/advanced**",
    async (route) => {
      await fulfillJson(route, {
        snapshots: [],
        missing_usernames: [requestedUsername],
        expired_usernames: [],
      })
    },
  )

  await page.route("**/api/v1/ig-scraper/jobs/apify", async (route) => {
    expect(route.request().method()).toBe("POST")
    await fulfillJson(route, {
      job_id: jobId,
      status: "queued",
    })
  })

  await page.route(`**/api/v1/ig-scraper/jobs/${jobId}`, async (route) => {
    await fulfillJson(route, {
      job_id: jobId,
      execution_mode: "apify",
      status: "done",
      created_at: "2026-04-25T00:00:00Z",
      updated_at: "2026-04-25T00:00:10Z",
      expires_at: "2026-04-26T00:00:00Z",
      attempts: 1,
      lease_owner: null,
      leased_until: null,
      heartbeat_at: null,
      summary: {
        usernames: [
          {
            username: readyUsername,
            status: "success",
            error: null,
          },
          {
            username: requestedUsername,
            status: "not_found",
            error: null,
          },
        ],
        counters: {
          requested: 2,
          successful: 1,
          failed: 0,
          not_found: 1,
        },
        error: null,
      },
      references: {
        all_usernames: [requestedUsername, readyUsername],
        successful_usernames: [readyUsername],
        failed_usernames: [],
        skipped_usernames: [],
        not_found_usernames: [requestedUsername],
      },
      error: null,
    })
  })
}

test.describe("Creators search scrape jobs", () => {
  test.use({
    storageState: anonymousStorageState,
  })

  test("creators_search_submit_usernames_reconciles_queued_job_to_completed_detail", async ({
    page,
  }) => {
    // Arrange
    await mockAuthenticatedSession(page)
    await mockAppShellApis(page)
    await mockCreatorsSearchApis(page)

    // Act
    await page.goto("/creators-search")
    await page
      .getByPlaceholder("creator_one, brand.partner, another_creator")
      .fill(requestedUsername)
    await page.keyboard.press("Enter")
    await page.getByRole("button", { name: "Buscar creadores" }).click()
    await expect(
      page.getByText("Usernames no encontrados").first(),
    ).toBeVisible()

    await page.getByRole("button", { exact: true, name: "Buscar" }).click()

    // Assert
    await expect(page.getByText(jobId)).toBeVisible()
    await expect(page.getByText("En cola")).toBeVisible()
    await expect(page.getByText("Esperando a que termine.")).toBeVisible()

    await page.evaluate(() => window.dispatchEvent(new Event("online")))

    await expect(page.getByText("Completado")).toBeVisible()
    await expect(
      page.getByText("Haz clic para revisar el resultado final."),
    ).toBeVisible()

    await page.getByText(jobId).click()

    await expect(page.getByText("DETALLE DEL JOB ACTUAL")).toBeVisible()
    await expect(
      page.getByText("Usernames listos", { exact: true }),
    ).toBeVisible()
    await expect(page.getByText(`@${readyUsername}`).first()).toBeVisible()
  })
})
