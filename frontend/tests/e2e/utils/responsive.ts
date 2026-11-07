import { expect, type Locator, type Page } from "@playwright/test"

export async function expectBounded(region: Locator) {
  await expect(region).toBeVisible()
  const bounds = await region.evaluate((element) => {
    const rect = element.getBoundingClientRect()
    return { left: rect.left, right: rect.right, viewport: innerWidth }
  })
  expect(bounds.left).toBeGreaterThanOrEqual(-1)
  expect(bounds.right).toBeLessThanOrEqual(bounds.viewport + 1)
}

export async function expectNoPageOverflow(page: Page) {
  await expect
    .poll(() =>
      page.evaluate(
        () =>
          document.documentElement.scrollWidth -
          document.documentElement.clientWidth,
      ),
    )
    .toBeLessThanOrEqual(1)
  const content = page.getByTestId("app-scroll")
  if (await content.count()) {
    await expect
      .poll(() =>
        content.evaluate(
          (element) => element.scrollWidth - element.clientWidth,
        ),
      )
      .toBeLessThanOrEqual(1)
  }
  // A clipped page can have a correct scrollWidth while hiding functional content.
  await expect
    .poll(() =>
      page.evaluate(() =>
        [
          ...document.querySelectorAll<HTMLElement>(
            "button, a, input, select, textarea, [data-local-scroll]",
          ),
        ]
          .filter((element) => {
            const rect = element.getBoundingClientRect()
            if (
              !rect.width ||
              !rect.height ||
              element.closest('[inert], [aria-hidden="true"]') ||
              getComputedStyle(element).visibility === "hidden"
            )
              return false
            if (
              !element.hasAttribute("data-local-scroll") &&
              element.closest("[data-local-scroll]")
            )
              return false
            return rect.left < -1 || rect.right > innerWidth + 1
          })
          .map((element) => ({
            tag: element.tagName,
            label: (
              element.getAttribute("aria-label") ||
              element.textContent ||
              ""
            ).slice(0, 60),
          }))
          .slice(0, 5),
      ),
    )
    .toEqual([])
}

export async function mockResponsiveSession(page: Page, admin = false) {
  await page.addInitScript(() => {
    localStorage.setItem("access_token", "responsive-test-token")
  })
  const user = {
    id: "responsive-user",
    email: "a_long_identity@example.com",
    full_name: "A creator with a very long display name for a narrow viewport",
    is_active: true,
    is_superuser: admin,
    access_profile: "standard",
    plan_status: "base",
  }
  const json = (body: unknown) => ({
    contentType: "application/json",
    body: JSON.stringify(body),
  })
  await page.route("**/api/v1/users/me", (r) => r.fulfill(json(user)))
  await page.route(/\/api\/v1\/users\/\?/, (r) =>
    r.fulfill(
      json({
        data: [{ ...user, id: "managed-user", is_superuser: false }],
        count: 9783,
      }),
    ),
  )
  await page.route("**/api/v1/billing/me", (r) =>
    r.fulfill(
      json({
        access_profile: "standard",
        managed_access_source: null,
        billing_eligible: true,
        trial_eligible: false,
        plan_status: "base",
        subscription_status: "active",
        access_revoked_reason: null,
        features: [],
        notices: [],
      }),
    ),
  )
  await page.route("**/api/v1/billing/notices", (r) =>
    r.fulfill(json({ data: [] })),
  )
  await page.route("**/api/v1/events/stream", (r) =>
    r.fulfill({ status: 403, body: "" }),
  )
  await page.route("**/api/v1/creators-search/history**", (r) =>
    r.fulfill(json({ items: [], count: 0 })),
  )
  await page.route("**/api/v1/ig-profiles/search**", (r) =>
    r.fulfill(
      json({
        profiles: [
          {
            _id: "profile-1",
            username: "selenagomez",
            full_name: "Selena Gomez",
            follower_count: 405000000,
            media_count: 2176,
            updated_date: "2025-01-01",
            ai_categories: [
              "Beauty / Skincare / Makeup",
              "Music / Dance / Entertainment",
            ],
            ai_roles: [
              "Expert / Professional / Authority",
              "Aspirational / Lifestyle",
            ],
          },
        ],
        pagination: {
          page: 1,
          page_size: 20,
          total: 9783,
          total_pages: 490,
          has_next: true,
          has_previous: false,
        },
      }),
    ),
  )
}
