import { expect, test } from "@playwright/test"
import {
  expectBounded,
  expectNoPageOverflow,
  mockResponsiveSession,
} from "./utils/responsive"
import { anonymousStorageState } from "./utils/storageState"

test.use({ storageState: anonymousStorageState })

for (const language of ["es", "en", "pt-BR"]) {
  test(`responsive_header_${language}_keeps_menu_and_actions_separate`, async ({
    page,
    context,
  }) => {
    // Arrange
    await mockResponsiveSession(page)
    await context.addCookies([
      {
        name: "kiizama.language",
        value: language,
        domain: "localhost",
        path: "/",
      },
    ])
    await page.setViewportSize({ width: 440, height: 956 })
    await page.goto("/creators-search")
    // Act / Assert
    const header = page.locator("header")
    await expect(header).toBeVisible()
    for (const width of [
      320, 360, 390, 440, 767, 768, 852, 853, 1024, 1108, 1109, 1280, 1920,
    ]) {
      await page.setViewportSize({ width, height: 956 })
      await expectNoPageOverflow(page)
      const buttons = header.locator("button:visible")
      for (const button of await buttons.all()) await expectBounded(button)
      const rects = await buttons.evaluateAll((elements) =>
        elements.map((e) => {
          const r = e.getBoundingClientRect()
          return { left: r.left, right: r.right }
        }),
      )
      for (let i = 1; i < rects.length; i++)
        expect(rects[i].left).toBeGreaterThanOrEqual(rects[i - 1].right)
    }
    await page.setViewportSize({ width: 440, height: 956 })
    // The navigation trigger must be owned by the header rather than floating over it.
    await expect(header.getByRole("button").first()).toHaveAttribute(
      "aria-label",
      /men[uú]/i,
    )
  })
}

test("responsive_browse_490_pages_keeps_filters_and_results_bounded", async ({
  page,
  context,
}) => {
  await mockResponsiveSession(page)
  await context.addCookies([
    { name: "kiizama.language", value: "en", domain: "localhost", path: "/" },
  ])
  await page.setViewportSize({ width: 440, height: 956 })
  await page.goto("/creators-search")
  await page.getByRole("tab").nth(1).click()
  await page.getByRole("button", { name: "SEARCH", exact: true }).click()
  await expect(page.getByText("Selena Gomez", { exact: true })).toBeVisible()
  for (const width of [
    320, 360, 390, 440, 767, 768, 852, 853, 1024, 1108, 1109, 1280, 1920,
  ]) {
    await page.setViewportSize({ width, height: 956 })
    await expectNoPageOverflow(page)
    await expectBounded(page.getByTestId("directory-filters-card"))
    await expectBounded(page.getByRole("navigation", { name: /pag/i }))
  }
})

test("responsive_settings_all_tabs_remain_reachable_without_page_overflow", async ({
  page,
}) => {
  await mockResponsiveSession(page)
  await page.setViewportSize({ width: 320, height: 700 })
  await page.goto("/settings")
  const tabs = page.getByRole("tablist").first().getByRole("tab")
  await expect(tabs).toHaveCount(6)
  await tabs.first().focus()
  await page.keyboard.press("End")
  await expect(tabs.last()).toHaveAttribute("aria-selected", "true")
  await expectBounded(tabs.last())
  for (const tab of await tabs.all()) {
    await tab.click()
    await expect(tab).toHaveAttribute("aria-selected", "true")
    await expectBounded(tab)
    await expectNoPageOverflow(page)
  }
})

test("responsive_admin_table_scrolls_locally_at_phone_and_tablet_widths", async ({
  page,
}) => {
  await mockResponsiveSession(page, true)
  await page.goto("/admin")
  await expect(page.getByRole("table")).toBeVisible()
  for (const width of [320, 440, 768, 1024]) {
    await page.setViewportSize({ width, height: 956 })
    await expectNoPageOverflow(page)
    const region = page.getByRole("region", {
      name: /users|usuarios|utilizadores/i,
    })
    await expectBounded(region)
    await region.focus()
    await expect(region).toBeFocused()
  }
})

test("responsive_notifications_fit_a_short_narrow_viewport", async ({
  page,
  context,
}) => {
  await mockResponsiveSession(page)
  await context.addCookies([
    { name: "kiizama.language", value: "en", domain: "localhost", path: "/" },
  ])
  await page.setViewportSize({ width: 320, height: 440 })
  await page.goto("/overview")
  await page.getByRole("button", { name: "Billing notices" }).click()
  await expectBounded(page.getByRole("menu"))
  await page.keyboard.press("Escape")
  await expect(page.getByRole("menu")).toBeHidden()
  await expectNoPageOverflow(page)
})

test("responsive_public_navbar_stays_bounded_at_intermediate_widths", async ({
  page,
}) => {
  await page.goto("/blog")
  await expect(page.locator("header")).toBeVisible()
  for (const width of [320, 440, 767, 768, 1024, 1279, 1280, 1920]) {
    await page.setViewportSize({ width, height: 956 })
    await expectNoPageOverflow(page)
    for (const control of await page.locator("header button:visible").all())
      await expectBounded(control)
  }
})

test("responsive_queries_stacked_card_fills_the_available_width", async ({
  page,
  context,
}) => {
  await mockResponsiveSession(page)
  await context.addCookies([
    { name: "kiizama.language", value: "en", domain: "localhost", path: "/" },
  ])
  await page.addInitScript(() => {
    const now = new Date().toISOString()
    const jobs = ["01a12dcd-4c68-7740-9548-31c5280c7c15", "previous-job"].map(
      (jobId) => ({
        jobId,
        sourceBox: "missing",
        requestedUsernames: ["alpha"],
        batchKey: "missing:alpha",
        status: "done",
        createdAt: now,
        updatedAt: now,
        readyUsernames: ["alpha"],
        error: null,
        terminalPayload: {
          event_version: 1,
          notification_id: jobId,
          job_id: jobId,
          status: "done",
          created_at: now,
          completed_at: now,
          requested_usernames: ["alpha"],
          ready_usernames: ["alpha"],
          successful_usernames: ["alpha"],
          skipped_usernames: [],
          failed_usernames: [],
          not_found_usernames: [],
          counters: { requested: 1, successful: 1, failed: 0, not_found: 0 },
          error: null,
        },
      }),
    )
    localStorage.setItem("kiizama-creators-search-jobs", JSON.stringify(jobs))
  })
  await page.setViewportSize({ width: 440, height: 956 })
  await page.goto("/creators-search")
  const card = page
    .getByText("01a12dcd-4c68-7740-9548-31c5280c7c15")
    .locator("xpath=../../..")
  const all = page.getByRole("button", { name: "View all (2)" })
  await expect(all).toBeVisible()
  const widths = await Promise.all([card.boundingBox(), all.boundingBox()])
  expect(Math.abs(widths[0]!.width - widths[1]!.width)).toBeLessThanOrEqual(1)
  await card.click()
  await expect(page.getByRole("dialog")).toBeVisible()
  await expectBounded(page.getByRole("dialog"))
})

test("responsive_drawer_navigation_restores_focus_and_resize_preserves_input", async ({
  page,
  context,
}) => {
  await mockResponsiveSession(page)
  await context.addCookies([
    { name: "kiizama.language", value: "en", domain: "localhost", path: "/" },
  ])
  await page.setViewportSize({ width: 440, height: 956 })
  await page.goto("/creators-search")
  await page
    .getByPlaceholder("creator_one, brand.partner, ...")
    .fill("creator_draft")
  await page.getByPlaceholder("creator_one, brand.partner, ...").press("Enter")
  const trigger = page.getByRole("button", { name: "Open menu", exact: true })
  await trigger.click()
  await expect(page.getByRole("dialog")).toBeVisible()
  await page.keyboard.press("Escape")
  await expect(trigger).toBeFocused()
  await page.setViewportSize({ width: 1280, height: 956 })
  await expect(page.getByText("@creator_draft", { exact: true })).toBeVisible()
  await page.setViewportSize({ width: 440, height: 956 })
  await trigger.click()
  await page.getByRole("dialog").getByRole("link", { name: "Settings" }).click()
  await expect(page.getByRole("tab")).toHaveCount(6)
  await expect(page.locator("header")).toHaveCount(1)
  await expect(page.getByRole("dialog")).toBeHidden()
})

test("responsive_notes_and_guide_keep_content_and_close_controls_reachable", async ({
  page,
  context,
}) => {
  await mockResponsiveSession(page)
  await context.addCookies([
    { name: "kiizama.language", value: "en", domain: "localhost", path: "/" },
  ])
  await page.setViewportSize({ width: 768, height: 956 })
  await page.goto("/overview")
  await page
    .getByRole("button", { name: "Notes and boards", exact: true })
    .click()
  const dialog = page.getByRole("dialog")
  await expectBounded(dialog)
  await dialog.getByRole("button", { name: "New note", exact: true }).click()
  await dialog
    .getByPlaceholder("Note title...")
    .fill("A very long note title that remains editable")
  await dialog
    .getByPlaceholder("Your own tag...")
    .fill("A_very_long_custom_tag_without_spaces_for_mobile")
  await dialog.getByRole("button", { name: "Add", exact: true }).click()
  await expect
    .poll(() => dialog.evaluate((e) => e.scrollWidth - e.clientWidth))
    .toBeLessThanOrEqual(1)
  await dialog.getByRole("button", { name: "New board", exact: true }).click()
  const board = dialog.getByRole("region", { name: "Untitled board" })
  await expectBounded(board)
  await board.focus()
  await page.keyboard.press("ArrowRight")
  for (const dimensions of [
    { width: 320, height: 700 },
    { width: 1026, height: 956 },
    { width: 1027, height: 956 },
    { width: 956, height: 440 },
  ]) {
    await page.setViewportSize(dimensions)
    await expectBounded(dialog)
    await expectBounded(board)
    const height = await dialog.boundingBox()
    expect(height!.height).toBeLessThanOrEqual(dimensions.height)
  }
  await page.keyboard.press("Escape")
  await page.getByRole("button", { name: "Open usage guide" }).click()
  await expectBounded(dialog)
  await dialog.getByRole("button", { name: "Close", exact: true }).click()
  await expect(dialog).toBeHidden()
})

for (const route of [
  "/",
  "/overview",
  "/brand-intelligence/reputation-strategy",
  "/login",
  "/signup",
  "/recover-password",
  "/reset-password",
  "/waiting-list",
  "/privacy",
  "/terms-conditions",
  "/security",
  "/cookie-notice",
  "/cookie-tables",
  "/about-us",
  "/providers",
  "/this-page-does-not-exist",
]) {
  test(`responsive_route_${route}_stays_bounded`, async ({ page }) => {
    if (route === "/overview" || route.includes("brand-intelligence"))
      await mockResponsiveSession(page)
    await page.route("**/api/v1/public/feature-flags/**", (r) =>
      r.fulfill({ status: 404, body: "{}" }),
    )
    await page.goto(route)
    // Some existing page titles are Text rather than headings; wait for actual content.
    if (["/login", "/signup", "/waiting-list"].includes(route))
      await expect(page.locator("form").first()).toBeVisible()
    else if (route === "/overview")
      await expect(
        page.getByTestId("app-scroll").getByText(/A creator with/),
      ).toBeVisible()
    else if (route === "/this-page-does-not-exist")
      await expect(page.getByTestId("not-found")).toBeVisible()
    else await expect(page.getByRole("heading").first()).toBeVisible()
    if (route.includes("brand-intelligence"))
      await expect(page.locator("form")).toBeVisible()
    for (const width of [320, 768, 1280]) {
      await page.setViewportSize({ width, height: 956 })
      await expectNoPageOverflow(page)
    }
  })
}

test("responsive_strategy_forms_keep_populated_summaries_and_validation_bounded", async ({
  page,
  context,
}) => {
  await mockResponsiveSession(page)
  await context.addCookies([
    { name: "kiizama.language", value: "en", domain: "localhost", path: "/" },
  ])
  await page.goto("/brand-intelligence/reputation-strategy")
  await page
    .getByPlaceholder("creator_one, creator.two, another_creator")
    .fill("creator_one")
  await page
    .getByPlaceholder("creator_one, creator.two, another_creator")
    .press("Enter")
  await page.getByPlaceholder("Acme Skincare").fill("Brand_".repeat(10))
  await page
    .getByPlaceholder(
      "Share the current business context, positioning, and what is happening around the brand.",
    )
    .fill("Context with a long narrative. ".repeat(15))
  for (const width of [320, 768, 1024, 1172, 1173, 1199, 1200, 1280, 1920]) {
    await page.setViewportSize({ width, height: 956 })
    await expectNoPageOverflow(page)
  }
  await page
    .getByRole("button", { name: "Reputation Creator Strategy", exact: true })
    .click()
  await page
    .getByPlaceholder("creator_one", { exact: true })
    .fill("creator_one")
  await page.getByPlaceholder("creator_one", { exact: true }).press("Enter")
  await page
    .getByPlaceholder(
      "Describe the creator's current narrative, positioning, and public perception.",
    )
    .fill("Creator context. ".repeat(15))
  for (const width of [320, 768, 1280]) {
    await page.setViewportSize({ width, height: 956 })
    await expectNoPageOverflow(page)
  }
  await page
    .getByRole("button", { name: "Reputation Campaign Strategy", exact: true })
    .click()
  await expect(page.getByPlaceholder("Acme Skincare")).toHaveValue(
    "Brand_".repeat(10),
  )
})

test("responsive_profile_dialog_keeps_wide_tables_local", async ({
  page,
  context,
}) => {
  await mockResponsiveSession(page)
  await context.addCookies([
    { name: "kiizama.language", value: "en", domain: "localhost", path: "/" },
  ])
  await page.route("**/api/v1/ig-profiles/profile-1/full-profile", (r) =>
    r.fulfill({
      contentType: "application/json",
      body: JSON.stringify({
        profile_id: "profile-1",
        scraped_at: "2026-11-07T00:00:00Z",
        profile: {
          _id: "profile-1",
          full_name: "Selena Gomez",
          username: "selenagomez",
          follower_count: 405000000,
          media_count: 2176,
          biography: "A long biography. ".repeat(20),
          updated_date: "2026-11-07",
          bio_links: [],
          ai_categories: [
            "Beauty / Skincare / Makeup",
            "Music / Dance / Entertainment",
          ],
          ai_roles: ["Expert / Professional / Authority"],
        },
        posts: [
          {
            profile_id: "profile-1",
            updated_at: "2026-11-07",
            posts: [
              {
                code: "post123",
                caption_text: "Long caption. ".repeat(30),
                like_count: 123,
                comment_count: 23,
              },
            ],
          },
        ],
        reels: [
          {
            profile_id: "profile-1",
            updated_at: "2026-11-07",
            reels: [
              {
                code: "reel123",
                play_count: 1234,
                like_count: 123,
                comment_count: 23,
              },
            ],
          },
        ],
      }),
    }),
  )
  await page.goto("/creators-search")
  await page.getByRole("tab").nth(1).click()
  await page.getByRole("button", { name: "SEARCH", exact: true }).click()
  await page
    .getByRole("button", { name: "View full profile", exact: true })
    .click()
  const dialog = page.getByRole("dialog")
  await expect(dialog.getByRole("table")).toHaveCount(2)
  for (const dimensions of [
    { width: 320, height: 700 },
    { width: 768, height: 956 },
    { width: 956, height: 440 },
    { width: 1920, height: 956 },
  ]) {
    await page.setViewportSize(dimensions)
    await expectBounded(dialog)
    expect((await dialog.boundingBox())!.width).toBeLessThanOrEqual(1100)
    await expect
      .poll(() => dialog.evaluate((e) => e.scrollWidth - e.clientWidth))
      .toBeLessThanOrEqual(1)
    for (const table of await dialog.locator("[data-local-scroll]").all()) {
      await table.scrollIntoViewIfNeeded()
      await expectBounded(table)
    }
  }
  await dialog.getByRole("button", { name: "Close", exact: true }).click()
  await expect(dialog).toBeHidden()
})

for (const language of ["en", "pt-BR"]) {
  test(`responsive_public_${language}_navigation_keeps_all_actions_reachable`, async ({
    page,
    context,
  }) => {
    await context.addCookies([
      {
        name: "kiizama.language",
        value: language,
        domain: "localhost",
        path: "/",
      },
    ])
    await page.route("**/api/v1/public/feature-flags/**", (r) =>
      r.fulfill({ status: 404, body: "{}" }),
    )
    await page.goto("/blog")
    await expect(page.locator("header")).toBeVisible()
    for (const width of [320, 768, 1279, 1280, 1920]) {
      await page.setViewportSize({ width, height: 956 })
      await expectNoPageOverflow(page)
      for (const control of await page.locator("header button:visible").all())
        await expectBounded(control)
    }
    await page.setViewportSize({ width: 320, height: 440 })
    const toggle = page.locator("header").getByRole("button", {
      name: language === "en" ? "Open menu" : "Abrir menu",
      exact: true,
    })
    await toggle.click()
    const signup = page.locator('header a[href$="/signup"]').last()
    await signup.scrollIntoViewIfNeeded()
    await expectBounded(signup)
    await signup.focus()
    await expect(signup).toBeFocused()
  })
}

test("responsive_real_blog_post_keeps_rich_content_bounded", async ({
  page,
}) => {
  await page.goto("/blog/tutorial-busqueda-creators-kiizama")
  await expect(page.getByTestId("blog-post-content")).toBeVisible()
  for (const width of [320, 440, 768, 1280]) {
    await page.setViewportSize({ width, height: 956 })
    await expectNoPageOverflow(page)
    await expectBounded(page.getByTestId("blog-post-content"))
  }
})

test("responsive_populated_notifications_wrap_inside_the_menu", async ({
  page,
  context,
}) => {
  await mockResponsiveSession(page)
  await context.addCookies([
    {
      name: "kiizama.language",
      value: "pt-BR",
      domain: "localhost",
      path: "/",
    },
  ])
  await page.route("**/api/v1/billing/notices", (r) =>
    r.fulfill({
      contentType: "application/json",
      body: JSON.stringify({
        data: [
          {
            id: "notice-1",
            status: "unread",
            title: "Aviso importante sobre sua assinatura ".repeat(4),
            message:
              "Detalhes sobre o próximo pagamento e o período da assinatura. ".repeat(
                10,
              ),
          },
        ],
      }),
    }),
  )
  await page.setViewportSize({ width: 320, height: 440 })
  await page.goto("/overview")
  await page.getByRole("button", { name: "Avisos de cobrança" }).click()
  const menu = page.getByRole("menu")
  await expectBounded(menu)
  await expect
    .poll(() => menu.evaluate((e) => e.scrollWidth - e.clientWidth))
    .toBeLessThanOrEqual(1)
  const bounds = await menu.boundingBox()
  expect(bounds!.y + bounds!.height).toBeLessThanOrEqual(440)
})

test("responsive_admin_dialogs_and_worker_form_keep_actions_reachable", async ({
  page,
  context,
}) => {
  await mockResponsiveSession(page, true)
  await context.addCookies([
    { name: "kiizama.language", value: "en", domain: "localhost", path: "/" },
  ])
  await page.setViewportSize({ width: 320, height: 440 })
  await page.goto("/admin")
  await page.getByRole("button", { name: "Add User", exact: true }).click()
  const dialog = page.getByRole("dialog")
  await expectBounded(dialog)
  await dialog.getByRole("button", { name: "Cancel", exact: true }).click()
  const actions = page.getByRole("button", { name: /^Actions for / })
  await actions.scrollIntoViewIfNeeded()
  await actions.click()
  await page.getByRole("button", { name: "Edit User", exact: true }).click()
  await expectBounded(dialog)
  await dialog.getByRole("button", { name: "Cancel", exact: true }).click()
  await page.getByRole("tab", { name: "Worker Jobs", exact: true }).click()
  await page
    .getByPlaceholder(
      "Paste usernames, commas, spaces, or Instagram profile URLs.",
    )
    .fill("creator_one, creator_two")
  await expectNoPageOverflow(page)
  await expectBounded(page.getByRole("button", { name: "Queue Worker Jobs" }))
})

test("responsive_cookie_choices_and_preferences_remain_reachable_in_short_viewports", async ({
  page,
  context,
}) => {
  await context.clearCookies()
  await context.addCookies([
    { name: "kiizama.language", value: "en", domain: "localhost", path: "/" },
  ])
  await page.setViewportSize({ width: 320, height: 440 })
  await page.goto("/blog")
  const dialog = page.getByRole("dialog")
  await expectBounded(dialog)
  await expectBounded(
    dialog.getByRole("button", {
      name: "Allow necessary cookies",
      exact: true,
    }),
  )
  await dialog
    .getByRole("button", { name: "Allow necessary cookies", exact: true })
    .click()
  await page
    .getByRole("button", { name: "Cookie Settings", exact: true })
    .click()
  await expectBounded(dialog)
  const done = dialog.getByRole("button", { name: "Done", exact: true })
  await done.scrollIntoViewIfNeeded()
  await expectBounded(done)
  const bounds = await dialog.boundingBox()
  expect(bounds!.height).toBeLessThanOrEqual(440)
  await done.click()
  await expect(dialog).toBeHidden()
})
