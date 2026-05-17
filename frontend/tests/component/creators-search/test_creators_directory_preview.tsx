import { screen, waitFor, within } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import { afterEach, beforeEach, describe, expect, test, vi } from "vitest"

import type { CreatorDirectorySearchResponse } from "../../../src/features/creators-directory/types"
import { CreatorsDirectoryPreview } from "../../../src/routes/_layout/-components/creators-search/CreatorsDirectoryPreview"
import { renderWithProviders } from "../helpers/render"

const {
  searchCreatorsDirectoryMock,
  getCreatorDirectoryFullProfileMock,
  enqueueCreatorsSearchScrapeJobsMock,
} = vi.hoisted(() => ({
  searchCreatorsDirectoryMock: vi.fn(),
  getCreatorDirectoryFullProfileMock: vi.fn(),
  enqueueCreatorsSearchScrapeJobsMock: vi.fn(),
}))

vi.mock("@/features/creators-directory/api", () => ({
  searchCreatorsDirectory: searchCreatorsDirectoryMock,
  getCreatorDirectoryFullProfile: getCreatorDirectoryFullProfileMock,
}))

vi.mock(
  "@/routes/_layout/-components/creators-search/creators-search.api",
  () => ({
    enqueueCreatorsSearchScrapeJobs: enqueueCreatorsSearchScrapeJobsMock,
  }),
)

const createSearchResponse = (
  overrides: Partial<CreatorDirectorySearchResponse> = {},
): CreatorDirectorySearchResponse => ({
  profiles: [],
  pagination: {
    page: 1,
    page_size: 20,
    total: 0,
    total_pages: 0,
    has_next: false,
    has_previous: false,
  },
  ...overrides,
})

describe("creators directory preview", () => {
  beforeEach(() => {
    searchCreatorsDirectoryMock.mockReset()
    getCreatorDirectoryFullProfileMock.mockReset()
    enqueueCreatorsSearchScrapeJobsMock.mockReset()
  })

  afterEach(() => {
    vi.clearAllMocks()
  })

  test("creators_directory_preview_initial_state_renders_idle_results", () => {
    renderWithProviders(<CreatorsDirectoryPreview />, { language: "en" })

    expect(
      screen.queryByTestId("directory-update-queue-card"),
    ).not.toBeInTheDocument()
    expect(
      screen.getByText("Run a search to explore saved creators."),
    ).toBeVisible()
    expect(
      screen.getByText(
        "Apply filters and click search to populate this panel with real profiles.",
      ),
    ).toBeVisible()
    expect(searchCreatorsDirectoryMock).not.toHaveBeenCalled()
  })

  test("creators_directory_preview_search_uses_selected_filters_and_omits_short_query", async () => {
    const user = userEvent.setup()
    searchCreatorsDirectoryMock.mockResolvedValue(
      createSearchResponse({
        pagination: {
          page: 1,
          page_size: 20,
          total: 0,
          total_pages: 0,
          has_next: false,
          has_previous: false,
        },
      }),
    )

    renderWithProviders(<CreatorsDirectoryPreview />, { language: "en" })
    const filterCard = screen.getByTestId("directory-filters-card")

    await user.click(screen.getByRole("button", { name: /Choose categories/i }))
    const categoryDialog = await screen.findByRole("dialog")
    await user.click(
      within(categoryDialog).getByRole("checkbox", { name: "Travel" }),
    )
    await user.click(
      within(categoryDialog).getByRole("button", { name: "Add" }),
    )

    await user.click(screen.getByRole("button", { name: /Choose roles/i }))
    const roleDialog = await screen.findByRole("dialog")
    await user.click(
      within(roleDialog).getByRole("checkbox", { name: "UGC Creator" }),
    )
    await user.click(within(roleDialog).getByRole("button", { name: "Add" }))

    await user.click(screen.getByRole("button", { name: /Choose range/i }))
    const rangeDialog = await screen.findByRole("dialog")
    const [minimumInput, maximumInput] =
      within(rangeDialog).getAllByRole("spinbutton")
    await user.clear(minimumInput)
    await user.type(minimumInput, "15000")
    await user.clear(maximumInput)
    await user.click(within(rangeDialog).getByRole("button", { name: "Add" }))

    await user.click(screen.getByRole("button", { name: /Choose order/i }))
    const sortDialog = await screen.findByRole("dialog")
    await user.click(
      within(sortDialog).getByRole("button", { name: "Username" }),
    )
    await user.click(within(sortDialog).getByRole("button", { name: "ASC" }))
    await user.click(within(sortDialog).getByRole("button", { name: "Add" }))

    await user.type(
      screen.getByPlaceholderText("Search by keyword, niche, or creator style"),
      "ab",
    )
    await user.click(screen.getByRole("button", { name: "SEARCH" }))

    await waitFor(() => {
      expect(searchCreatorsDirectoryMock).toHaveBeenCalledWith({
        ai_categories: ["Travel"],
        ai_roles: ["UGC Creator"],
        follower_count_min: 15000,
        follower_count_max: undefined,
        page: 1,
        page_size: 20,
        query: undefined,
        sort_by: "username",
        sort_order: "asc",
      })
    })

    expect(within(filterCard).getByText("Travel")).toBeVisible()
    expect(within(filterCard).getByText("UGC Creator")).toBeVisible()
    expect(within(filterCard).getByText("Min 15000")).toBeVisible()
    expect(within(filterCard).getByText("Username")).toBeVisible()
    expect(within(filterCard).getByText("ASC")).toBeVisible()
    expect(screen.getByText("No creators matched this search.")).toBeVisible()
  })

  test("creators_directory_preview_loading_and_results_render_real_profiles", async () => {
    const user = userEvent.setup()
    let resolveSearch!: (value: CreatorDirectorySearchResponse) => void

    searchCreatorsDirectoryMock.mockImplementation(
      () =>
        new Promise<CreatorDirectorySearchResponse>((resolve) => {
          resolveSearch = resolve
        }),
    )

    renderWithProviders(<CreatorsDirectoryPreview />, { language: "en" })

    await user.type(
      screen.getByPlaceholderText("Search by keyword, niche, or creator style"),
      "fitness",
    )
    await user.click(screen.getByRole("button", { name: "SEARCH" }))

    await waitFor(() => {
      expect(searchCreatorsDirectoryMock).toHaveBeenCalledWith({
        ai_categories: [],
        ai_roles: [],
        follower_count_min: 1,
        follower_count_max: undefined,
        page: 1,
        page_size: 20,
        query: "fitness",
        sort_by: "follower_count",
        sort_order: "desc",
      })
    })

    await waitFor(() => {
      expect(
        screen.queryByText("Run a search to explore saved creators."),
      ).not.toBeInTheDocument()
    })

    resolveSearch(
      createSearchResponse({
        profiles: [
          {
            _id: "profile_1",
            ig_id: "ig_1",
            username: "fit_alpha",
            full_name: "Fit Alpha",
            biography: "Performance creator",
            is_private: false,
            is_verified: true,
            profile_pic_url: "",
            updated_date: "2026-05-15T12:00:00Z",
            follower_count: 45200,
            following_count: 210,
            media_count: 184,
            ai_categories: ["Fitness", "Health"],
            ai_roles: ["Affiliate Creator"],
          },
          {
            _id: "profile_2",
            ig_id: "ig_2",
            username: "wellness_beta",
            full_name: "Wellness Beta",
            biography: "Lifestyle creator",
            is_private: false,
            is_verified: false,
            profile_pic_url: "",
            updated_date: "2026-05-10T12:00:00Z",
            follower_count: 12000,
            following_count: 180,
            media_count: 64,
            ai_categories: [],
            ai_roles: [],
          },
        ],
        pagination: {
          page: 1,
          page_size: 20,
          total: 2,
          total_pages: 1,
          has_next: false,
          has_previous: false,
        },
      }),
    )

    expect(await screen.findByText("Fit Alpha")).toBeVisible()
    expect(screen.getByText("@fit_alpha")).toBeVisible()
    expect(screen.getByText("Current")).toBeVisible()
    expect(screen.getAllByText("Update").length).toBeGreaterThan(0)
    expect(screen.getByText("Fitness, Health")).toBeVisible()
    expect(screen.getByText("No curated category")).toBeVisible()
    expect(screen.getAllByText("Media")).toHaveLength(2)
    expect(screen.getByText("184")).toBeVisible()
  })

  test("creators_directory_preview_pagination_reuses_applied_filters", async () => {
    const user = userEvent.setup()

    searchCreatorsDirectoryMock
      .mockResolvedValueOnce(
        createSearchResponse({
          profiles: [
            {
              _id: "profile_1",
              ig_id: "ig_1",
              username: "alpha_creator",
              full_name: "Alpha Creator",
              biography: "",
              is_private: false,
              is_verified: false,
              profile_pic_url: "",
              updated_date: "2026-05-15T12:00:00Z",
              follower_count: 25000,
              following_count: 120,
              media_count: 40,
              ai_categories: ["Travel"],
              ai_roles: ["UGC Creator"],
            },
          ],
          pagination: {
            page: 1,
            page_size: 20,
            total: 25,
            total_pages: 2,
            has_next: true,
            has_previous: false,
          },
        }),
      )
      .mockResolvedValueOnce(
        createSearchResponse({
          profiles: [
            {
              _id: "profile_2",
              ig_id: "ig_2",
              username: "beta_creator",
              full_name: "Beta Creator",
              biography: "",
              is_private: false,
              is_verified: false,
              profile_pic_url: "",
              updated_date: "2026-05-14T12:00:00Z",
              follower_count: 22000,
              following_count: 80,
              media_count: 37,
              ai_categories: ["Travel"],
              ai_roles: ["UGC Creator"],
            },
          ],
          pagination: {
            page: 2,
            page_size: 20,
            total: 25,
            total_pages: 2,
            has_next: false,
            has_previous: true,
          },
        }),
      )

    renderWithProviders(<CreatorsDirectoryPreview />, { language: "en" })

    await user.type(
      screen.getByPlaceholderText("Search by keyword, niche, or creator style"),
      "travel",
    )
    await user.click(screen.getByRole("button", { name: "SEARCH" }))

    expect(await screen.findByText("Alpha Creator")).toBeVisible()

    await user.click(screen.getByRole("button", { name: /page 2/i }))

    await waitFor(() => {
      expect(searchCreatorsDirectoryMock).toHaveBeenNthCalledWith(2, {
        ai_categories: [],
        ai_roles: [],
        follower_count_min: 1,
        follower_count_max: undefined,
        page: 2,
        page_size: 20,
        query: "travel",
        sort_by: "follower_count",
        sort_order: "desc",
      })
    })

    expect(await screen.findByText("Beta Creator")).toBeVisible()
  })

  test("creators_directory_preview_error_state_keeps_filters_visible", async () => {
    const user = userEvent.setup()
    searchCreatorsDirectoryMock.mockRejectedValue(
      new Error("Backend unavailable"),
    )

    renderWithProviders(<CreatorsDirectoryPreview />, { language: "en" })

    await user.click(screen.getByRole("button", { name: "SEARCH" }))

    expect(await screen.findByText("Search failed")).toBeVisible()
    expect(screen.getByText("Backend unavailable")).toBeVisible()
    expect(screen.getByText("Min 1")).toBeVisible()
    expect(screen.getByText("Follower count")).toBeVisible()
    expect(screen.getByText("DESC")).toBeVisible()
  })

  test("creators_directory_preview_reset_restores_default_filters_and_idle_state", async () => {
    const user = userEvent.setup()
    searchCreatorsDirectoryMock.mockResolvedValue(
      createSearchResponse({
        profiles: [
          {
            _id: "profile_1",
            ig_id: "ig_1",
            username: "travel_alpha",
            full_name: "Travel Alpha",
            biography: "",
            is_private: false,
            is_verified: false,
            profile_pic_url: "",
            updated_date: "2026-05-15T12:00:00Z",
            follower_count: 25000,
            following_count: 120,
            media_count: 40,
            ai_categories: ["Travel"],
            ai_roles: ["UGC Creator"],
          },
        ],
        pagination: {
          page: 1,
          page_size: 20,
          total: 1,
          total_pages: 1,
          has_next: false,
          has_previous: false,
        },
      }),
    )

    renderWithProviders(<CreatorsDirectoryPreview />, { language: "en" })
    const filterCard = screen.getByTestId("directory-filters-card")

    await user.click(screen.getByRole("button", { name: /Choose categories/i }))
    const categoryDialog = await screen.findByRole("dialog")
    await user.click(
      within(categoryDialog).getByRole("checkbox", { name: "Travel" }),
    )
    await user.click(
      within(categoryDialog).getByRole("button", { name: "Add" }),
    )

    await user.type(
      screen.getByPlaceholderText("Search by keyword, niche, or creator style"),
      "travel",
    )
    await user.click(screen.getByRole("button", { name: "SEARCH" }))

    expect(await screen.findByText("Travel Alpha")).toBeVisible()

    await user.click(screen.getByRole("button", { name: "Restore defaults" }))

    expect(
      screen.getByText("Run a search to explore saved creators."),
    ).toBeVisible()
    expect(
      screen.getByPlaceholderText("Search by keyword, niche, or creator style"),
    ).toHaveValue("")
    expect(within(filterCard).queryByText("Travel")).not.toBeInTheDocument()
    expect(within(filterCard).getByText("Min 1")).toBeVisible()
    expect(within(filterCard).getByText("Follower count")).toBeVisible()
    expect(within(filterCard).getByText("DESC")).toBeVisible()
    expect(screen.queryByText("Travel Alpha")).not.toBeInTheDocument()
  })

  test("creators_directory_preview_update_queue_adds_and_removes_profiles", async () => {
    const user = userEvent.setup()

    searchCreatorsDirectoryMock.mockResolvedValue(
      createSearchResponse({
        profiles: [
          {
            _id: "profile_1",
            ig_id: "ig_1",
            username: "travel_alpha",
            full_name: "Travel Alpha",
            biography: "",
            is_private: false,
            is_verified: false,
            profile_pic_url: "",
            updated_date: "2026-05-01T12:00:00Z",
            follower_count: 25000,
            following_count: 120,
            media_count: 40,
            ai_categories: ["Travel"],
            ai_roles: ["UGC Creator"],
          },
        ],
        pagination: {
          page: 1,
          page_size: 20,
          total: 1,
          total_pages: 1,
          has_next: false,
          has_previous: false,
        },
      }),
    )

    renderWithProviders(<CreatorsDirectoryPreview />, { language: "en" })

    await user.click(screen.getByRole("button", { name: "SEARCH" }))
    expect(await screen.findByText("Travel Alpha")).toBeVisible()

    await user.click(screen.getByRole("button", { name: "Update list" }))

    const queueCard = screen.getByTestId("directory-update-queue-card")
    expect(within(queueCard).getByText("@travel_alpha")).toBeVisible()
    expect(screen.getByRole("button", { name: "Added" })).toBeDisabled()

    await user.click(screen.getByRole("button", { name: "Remove" }))

    expect(
      screen.queryByTestId("directory-update-queue-card"),
    ).not.toBeInTheDocument()
    expect(screen.getByRole("button", { name: "Update list" })).toBeEnabled()
  })

  test("creators_directory_preview_update_queue_submits_jobs_and_requests_direct_tab_focus", async () => {
    const user = userEvent.setup()
    const onRequestDirectSearchFocus = vi.fn()

    searchCreatorsDirectoryMock.mockResolvedValue(
      createSearchResponse({
        profiles: [
          {
            _id: "profile_1",
            ig_id: "ig_1",
            username: "travel_alpha",
            full_name: "Travel Alpha",
            biography: "",
            is_private: false,
            is_verified: false,
            profile_pic_url: "",
            updated_date: "2026-05-01T12:00:00Z",
            follower_count: 25000,
            following_count: 120,
            media_count: 40,
            ai_categories: ["Travel"],
            ai_roles: ["UGC Creator"],
          },
          {
            _id: "profile_2",
            ig_id: "ig_2",
            username: "food_beta",
            full_name: "Food Beta",
            biography: "",
            is_private: false,
            is_verified: false,
            profile_pic_url: "",
            updated_date: "2026-05-02T12:00:00Z",
            follower_count: 18000,
            following_count: 80,
            media_count: 32,
            ai_categories: ["Food"],
            ai_roles: ["Affiliate Creator"],
          },
        ],
        pagination: {
          page: 1,
          page_size: 20,
          total: 2,
          total_pages: 1,
          has_next: false,
          has_previous: false,
        },
      }),
    )
    enqueueCreatorsSearchScrapeJobsMock.mockResolvedValue({
      batchCount: 1,
      createdCount: 1,
      skippedCount: 0,
    })

    renderWithProviders(
      <CreatorsDirectoryPreview
        onRequestDirectSearchFocus={onRequestDirectSearchFocus}
      />,
      { language: "en" },
    )

    await user.click(screen.getByRole("button", { name: "SEARCH" }))
    expect(await screen.findByText("Travel Alpha")).toBeVisible()

    await user.click(screen.getAllByRole("button", { name: "Update list" })[0])
    await user.click(screen.getAllByRole("button", { name: "Update list" })[0])

    await user.click(screen.getByRole("button", { name: "Update" }))

    await waitFor(() => {
      expect(enqueueCreatorsSearchScrapeJobsMock).toHaveBeenCalledWith(
        "expired",
        ["travel_alpha", "food_beta"],
      )
    })

    expect(onRequestDirectSearchFocus).toHaveBeenCalledTimes(1)
    expect(
      screen.queryByTestId("directory-update-queue-card"),
    ).not.toBeInTheDocument()
  })

  test("creators_directory_preview_view_full_profile_loads_snapshot_detail", async () => {
    const user = userEvent.setup()

    searchCreatorsDirectoryMock.mockResolvedValue(
      createSearchResponse({
        profiles: [
          {
            _id: "profile_1",
            ig_id: "ig_1",
            username: "travel_alpha",
            full_name: "Travel Alpha",
            biography: "",
            is_private: false,
            is_verified: false,
            profile_pic_url: "",
            updated_date: "2026-05-15T12:00:00Z",
            follower_count: 25000,
            following_count: 120,
            media_count: 40,
            ai_categories: ["Travel"],
            ai_roles: ["UGC Creator"],
          },
        ],
        pagination: {
          page: 1,
          page_size: 20,
          total: 1,
          total_pages: 1,
          has_next: false,
          has_previous: false,
        },
      }),
    )

    getCreatorDirectoryFullProfileMock.mockResolvedValue({
      _id: "snapshot_1",
      profile_id: "profile_1",
      scraped_at: "2026-05-15T12:00:00Z",
      profile: {
        _id: "profile_1",
        ig_id: "ig_1",
        username: "travel_alpha",
        full_name: "Travel Alpha",
        biography: "Travel creator",
        is_private: false,
        is_verified: false,
        profile_pic_url: "",
        updated_date: "2026-05-15T12:00:00Z",
        follower_count: 25000,
        following_count: 120,
        media_count: 40,
        ai_categories: ["Travel"],
        ai_roles: ["UGC Creator"],
      },
      posts: [],
      reels: [],
      metrics: null,
      update_required: false,
    })

    renderWithProviders(<CreatorsDirectoryPreview />, { language: "en" })

    await user.click(screen.getByRole("button", { name: "SEARCH" }))
    expect(await screen.findByText("Travel Alpha")).toBeVisible()

    await user.click(screen.getByRole("button", { name: "View full profile" }))

    await waitFor(() => {
      expect(getCreatorDirectoryFullProfileMock).toHaveBeenCalledWith(
        "profile_1",
      )
    })

    expect(await screen.findByRole("dialog")).toBeVisible()
    expect(screen.getAllByText("Travel Alpha").length).toBeGreaterThan(0)
    expect(screen.getByText("Travel creator")).toBeVisible()
  })
})
