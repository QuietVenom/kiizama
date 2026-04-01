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

const mockUsersApi = async (
  page: Page,
  options: {
    meStatus: number
    meBody: unknown
    usersStatus?: number
    usersBody?: unknown
  },
) => {
  await page.route("**/api/v1/users/**", async (route) => {
    const url = new URL(route.request().url())

    if (url.pathname === "/api/v1/users/me") {
      await route.fulfill({
        status: options.meStatus,
        contentType: "application/json",
        body: JSON.stringify(options.meBody),
      })
      return
    }

    if (url.pathname === "/api/v1/users/") {
      await route.fulfill({
        status: options.usersStatus ?? 200,
        contentType: "application/json",
        body: JSON.stringify(
          options.usersBody ?? {
            data: [],
            count: 0,
          },
        ),
      })
      return
    }

    await route.continue()
  })
}

test.describe("HTTP error routes", () => {
  test.use({
    storageState: anonymousStorageState,
  })

  test("stays on login and clears an expired stored session", async ({
    page,
  }) => {
    await mockAuthenticatedSession(page)
    await mockUsersApi(page, {
      meStatus: 401,
      meBody: { detail: "Unauthorized" },
    })

    await page.goto("/login")

    await expect(page).toHaveURL(/\/login$/)
    await expect(page.getByPlaceholder("Email")).toBeVisible()
  })

  test("redirects to login with redirect when current session is invalid", async ({
    page,
  }) => {
    await mockAuthenticatedSession(page)
    await mockUsersApi(page, {
      meStatus: 401,
      meBody: { detail: "Unauthorized" },
    })

    await page.goto("/overview")

    await expect(page).toHaveURL(/\/login\?redirect=%2Foverview$/)
  })

  for (const scenario of [
    {
      status: 403,
      testId: "forbidden",
      name: "renders forbidden when a critical admin query is denied",
    },
    {
      status: 500,
      testId: "server-error",
      name: "renders server error when a critical admin query fails unexpectedly",
    },
    {
      status: 503,
      testId: "service-unavailable",
      name: "renders service unavailable when a critical admin query is unavailable",
    },
  ] as const) {
    test(scenario.name, async ({ page }) => {
      await mockAuthenticatedSession(page)
      await mockUserEventsStream(page)
      await mockUsersApi(page, {
        meStatus: 200,
        meBody: {
          id: "test-user-id",
          email: "admin@example.com",
          full_name: "Admin User",
          is_active: true,
          is_superuser: true,
        },
        usersStatus: scenario.status,
        usersBody: { detail: "Request failed." },
      })

      await page.goto("/admin")

      await expect(page.getByTestId(scenario.testId)).toBeVisible()
    })
  }
})
