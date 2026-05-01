import { expect, type Page, type Route, test } from "@playwright/test"

import { anonymousStorageState } from "./utils/storageState"

const creatorUsername = "creator_one"

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
          code: "reputation_strategy",
          name: "Reputation Strategy",
          limit: 10,
          used: 0,
          reserved: 0,
          remaining: 10,
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
}

const mockProfilesExistence = async (page: Page) => {
  await page.route(
    "**/api/v1/brand-intelligence/profiles-existence**",
    async (route) => {
      await fulfillJson(route, {
        profiles: [
          {
            username: creatorUsername,
            exists: true,
            expired: false,
          },
        ],
      })
    },
  )
}

const mockReportDownload = async ({
  assertPayload,
  contentType,
  endpointPath,
  filename,
  page,
}: {
  assertPayload: (payload: Record<string, unknown>) => void
  contentType: "application/pdf" | "application/zip"
  endpointPath: string
  filename: string
  page: Page
}) => {
  await page.route(`**${endpointPath}`, async (route) => {
    expect(route.request().method()).toBe("POST")
    assertPayload(route.request().postDataJSON() as Record<string, unknown>)

    await route.fulfill({
      status: 200,
      contentType,
      headers: {
        "Access-Control-Expose-Headers": "Content-Disposition",
        "Content-Disposition": `attachment; filename="${filename}"`,
      },
      body:
        contentType === "application/pdf"
          ? "%PDF-1.4 mocked report"
          : "PK mocked zip report",
    })
  })
}

const fillCampaignStrategyForm = async (page: Page) => {
  await page
    .getByRole("combobox", { name: /Brand goal/i })
    .selectOption("Trust & Credibility Acceleration")
  await page
    .getByPlaceholder("creator_one, creator.two, another_creator")
    .fill(creatorUsername)
  await page.keyboard.press("Enter")
  await page.getByRole("button", { name: "Validate profiles" }).click()
  await expect(page.getByText("1 checked")).toBeVisible()

  await page.getByRole("textbox", { name: /Brand name/i }).fill("Kiizama")
  await page
    .getByRole("textbox", { name: /Brand context/i })
    .fill("Lifestyle brand context.")
  await page
    .getByRole("textbox", { name: /Goal context/i })
    .fill("Launch a high-trust creator campaign.")
  await page
    .getByRole("combobox", { name: /Timeframe/i })
    .selectOption("3 months")
  await page
    .getByRole("combobox", { name: /Campaign type/i })
    .selectOption("all_nano_seeding_ugc_flood")
  await page.getByRole("button", { name: "Gen Z" }).click()
}

const fillCreatorStrategyForm = async (page: Page) => {
  await page
    .getByRole("button", { name: /Reputation Creator Strategy/i })
    .click()
  await page.getByPlaceholder("creator_one").fill(creatorUsername)
  await page.keyboard.press("Enter")
  await page.getByRole("button", { name: "Validate profile" }).click()
  await expect(page.getByText("1 checked")).toBeVisible()

  await page
    .getByRole("combobox", { name: /Goal type/i })
    .selectOption("Community Trust")
  await page
    .getByRole("combobox", { name: /Timeframe/i })
    .selectOption("6 months")
  await page
    .getByRole("textbox", { name: /Creator context/i })
    .fill("Creator reputation context.")
  await page
    .getByRole("textbox", { name: /Goal context/i })
    .fill("Improve trust and brand readiness.")
  await page.getByRole("button", { name: "Gen Z" }).click()
  await page
    .getByRole("textbox", { name: /Primary platforms/i })
    .fill("Instagram")
}

test.describe("Brand Intelligence report generation", () => {
  test.use({
    storageState: anonymousStorageState,
  })

  test("brand_intelligence_campaign_strategy_generates_pdf_download", async ({
    page,
  }) => {
    // Arrange
    await mockAuthenticatedSession(page)
    await mockAppShellApis(page)
    await mockProfilesExistence(page)
    await mockReportDownload({
      page,
      endpointPath: "/api/v1/brand-intelligence/reputation-campaign-strategy",
      filename: "campaign-strategy.pdf",
      contentType: "application/pdf",
      assertPayload: (payload) => {
        expect(payload).toMatchObject({
          brand_name: "Kiizama",
          generate_pdf: true,
          profiles_list: [creatorUsername],
        })
      },
    })

    // Act
    await page.goto("/brand-intelligence/reputation-strategy")
    await expect(
      page.getByRole("heading", {
        name: "Build modular reputation strategy reports.",
      }),
    ).toBeVisible()
    await fillCampaignStrategyForm(page)
    const downloadPromise = page.waitForEvent("download")
    await page.getByRole("button", { name: "Generate PDF report" }).click()
    const download = await downloadPromise

    // Assert
    expect(download.suggestedFilename()).toBe("campaign-strategy.pdf")
    await expect(
      page.getByText("Report ready: campaign-strategy.pdf"),
    ).toBeVisible()
  })

  test("brand_intelligence_creator_strategy_generates_zip_download", async ({
    page,
  }) => {
    // Arrange
    await mockAuthenticatedSession(page)
    await mockAppShellApis(page)
    await mockProfilesExistence(page)
    await mockReportDownload({
      page,
      endpointPath: "/api/v1/brand-intelligence/reputation-creator-strategy",
      filename: "creator-strategy.zip",
      contentType: "application/zip",
      assertPayload: (payload) => {
        expect(payload).toMatchObject({
          creator_username: creatorUsername,
          generate_pdf: true,
          primary_platforms: ["Instagram"],
        })
      },
    })

    // Act
    await page.goto("/brand-intelligence/reputation-strategy")
    await expect(
      page.getByRole("heading", {
        name: "Build modular reputation strategy reports.",
      }),
    ).toBeVisible()
    await fillCreatorStrategyForm(page)
    const downloadPromise = page.waitForEvent("download")
    await page.getByRole("button", { name: "Generate PDF report" }).click()
    const download = await downloadPromise

    // Assert
    expect(download.suggestedFilename()).toBe("creator-strategy.zip")
    await expect(
      page.getByText("Report ready: creator-strategy.zip"),
    ).toBeVisible()
  })
})
