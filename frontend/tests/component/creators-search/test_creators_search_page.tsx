import { screen, waitFor } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import { beforeEach, describe, expect, test, vi } from "vitest"

import {
  type BillingSummary,
  billingSummaryQueryKey,
} from "../../../src/features/billing/api"
import type { IgScrapeTerminalEventPayload } from "../../../src/features/user-events/types"
import {
  CREATORS_SEARCH_JOBS_STORAGE_KEY,
  type CreatorsSearchLocalJob,
} from "../../../src/lib/creators-search-jobs"
import { createTestQueryClient, renderWithProviders } from "../helpers/render"

const { listCreatorsSearchHistoryMock, router } = vi.hoisted(() => ({
  listCreatorsSearchHistoryMock: vi.fn(),
  router: {
    navigate: vi.fn(),
  },
}))

vi.mock("@tanstack/react-router", () => ({
  useNavigate: () => router.navigate,
}))

vi.mock("@/client", async (importActual) => {
  const actual = await importActual<typeof import("@/client")>()
  return {
    ...actual,
    CreatorsSearchHistoryService: {
      ...actual.CreatorsSearchHistoryService,
      listCreatorsSearchHistory: listCreatorsSearchHistoryMock,
    },
  }
})

vi.mock("@/components/Dashboard/DashboardTopbar", () => ({
  default: () => <div>Dashboard topbar</div>,
}))

vi.mock(
  "@/routes/_layout/-components/creators-search/DirectCreatorsSearchTab",
  () => ({
    default: (props: { onOpenHistory: () => void; usernames: string[] }) => (
      <section>
        <div>Direct creators search content</div>
        <div data-testid="tab-usernames">{props.usernames.join(" ")}</div>
        <button type="button" onClick={props.onOpenHistory}>
          open history from tab
        </button>
      </section>
    ),
  }),
)

const { CreatorsSearchPage } = await import(
  "../../../src/routes/_layout/-components/creators-search/CreatorsSearchPage"
)

const createBillingSummary = (
  overrides: Partial<BillingSummary> = {},
): BillingSummary => ({
  access_profile: "standard",
  access_revoked_reason: null,
  billing_eligible: true,
  cancel_at: null,
  current_period_end: null,
  current_period_start: null,
  features: [],
  latest_invoice_status: null,
  managed_access_source: null,
  notices: [],
  pending_ambassador_activation: false,
  plan_status: "base",
  renewal_day: null,
  subscription_status: "active",
  trial_eligible: false,
  ...overrides,
})

const createTerminalPayload = (
  jobId: string,
  readyUsernames: string[],
): IgScrapeTerminalEventPayload => ({
  event_version: 1,
  notification_id: `notification_${jobId}`,
  job_id: jobId,
  status: "done",
  created_at: "2026-01-01T00:00:00Z",
  completed_at: "2026-01-01T00:01:00Z",
  requested_usernames: readyUsernames,
  ready_usernames: readyUsernames,
  successful_usernames: readyUsernames,
  skipped_usernames: [],
  failed_usernames: [],
  not_found_usernames: [],
  counters: {
    requested: readyUsernames.length,
    successful: readyUsernames.length,
    failed: 0,
    not_found: 0,
  },
  error: null,
})

const createDoneJob = (
  jobId: string,
  readyUsernames: string[] = ["alpha"],
): CreatorsSearchLocalJob => ({
  batchKey: `expired:${readyUsernames.join(",")}`,
  createdAt: "2026-01-01T00:00:00Z",
  error: null,
  jobId,
  readyUsernames,
  requestedUsernames: readyUsernames,
  sourceBox: "expired",
  status: "done",
  terminalPayload: createTerminalPayload(jobId, readyUsernames),
  updatedAt: "2026-01-01T00:01:00Z",
})

const seedCurrentJobs = (jobs: CreatorsSearchLocalJob[]) => {
  localStorage.setItem(CREATORS_SEARCH_JOBS_STORAGE_KEY, JSON.stringify(jobs))
}

const renderCreatorsSearchPage = (billing: BillingSummary) => {
  const queryClient = createTestQueryClient()
  queryClient.setQueryData(billingSummaryQueryKey, billing)
  return renderWithProviders(<CreatorsSearchPage />, {
    language: "en",
    queryClient,
  })
}

describe("creators search page", () => {
  beforeEach(() => {
    router.navigate.mockClear()
    listCreatorsSearchHistoryMock.mockReset()
    localStorage.removeItem(CREATORS_SEARCH_JOBS_STORAGE_KEY)
  })

  test("creators_search_page_initial_state_renders_direct_search_tab", async () => {
    // Arrange / Act
    renderCreatorsSearchPage(createBillingSummary())

    // Assert
    expect(screen.getByText("Creators Search")).toBeVisible()
    expect(screen.getByText("Direct Creator Search")).toBeVisible()
    expect(screen.getByText("Browse by Category or Role")).toBeVisible()
    expect(
      await screen.findByText("Direct creators search content"),
    ).toBeVisible()
  })

  test("creators_search_page_directory_tab_selection_renders_directory_preview", async () => {
    // Arrange
    const user = userEvent.setup()
    renderCreatorsSearchPage(createBillingSummary())

    // Act
    await user.click(
      screen.getByRole("tab", { name: /Browse by Category or Role/i }),
    )

    // Assert
    expect(
      await screen.findByText("Run a search to explore saved creators."),
    ).toBeVisible()
  })

  test("creators_search_page_locked_user_directory_tab_renders_paywall", async () => {
    // Arrange
    const user = userEvent.setup()
    renderCreatorsSearchPage(
      createBillingSummary({
        plan_status: "none",
        subscription_status: null,
        trial_eligible: false,
      }),
    )

    // Act
    await user.click(
      screen.getByRole("tab", { name: /Browse by Category or Role/i }),
    )

    // Assert
    expect(
      await screen.findByText("Unlock the creators directory"),
    ).toBeVisible()
    expect(
      screen.getByRole("button", { name: "Activate your subscription" }),
    ).toBeVisible()
    expect(
      screen.getByLabelText("Requires an active subscription"),
    ).toBeVisible()
    expect(
      screen.queryByText("Run a search to explore saved creators."),
    ).not.toBeInTheDocument()
  })

  test("creators_search_page_locked_trial_eligible_cta_navigates_to_payments", async () => {
    // Arrange
    const user = userEvent.setup()
    renderCreatorsSearchPage(
      createBillingSummary({
        plan_status: "none",
        subscription_status: null,
        trial_eligible: true,
      }),
    )
    await user.click(
      screen.getByRole("tab", { name: /Browse by Category or Role/i }),
    )

    // Act
    await user.click(
      await screen.findByRole("button", { name: "Start your 7-day trial" }),
    )

    // Assert
    expect(router.navigate).toHaveBeenCalledWith({
      to: "/settings",
      search: { tab: "payments" },
    })
  })

  test("creators_search_page_paused_subscription_directory_tab_renders_paywall", async () => {
    // Arrange: post-trial paused subscriptions still report plan_status "base".
    const user = userEvent.setup()
    renderCreatorsSearchPage(
      createBillingSummary({
        plan_status: "base",
        subscription_status: "paused",
      }),
    )

    // Act
    await user.click(
      screen.getByRole("tab", { name: /Browse by Category or Role/i }),
    )

    // Assert
    expect(
      await screen.findByText("Unlock the creators directory"),
    ).toBeVisible()
  })

  test("creators_search_page_pending_ambassador_renders_directory_preview", async () => {
    // Arrange
    const user = userEvent.setup()
    renderCreatorsSearchPage(
      createBillingSummary({
        access_profile: "ambassador",
        managed_access_source: null,
        pending_ambassador_activation: true,
        plan_status: "none",
        subscription_status: null,
      }),
    )

    // Act
    await user.click(
      screen.getByRole("tab", { name: /Browse by Category or Role/i }),
    )

    // Assert
    expect(
      await screen.findByText("Run a search to explore saved creators."),
    ).toBeVisible()
  })

  test("creators_search_page_without_jobs_hides_jobs_summary", () => {
    // Arrange / Act
    renderCreatorsSearchPage(createBillingSummary())

    // Assert
    expect(screen.queryByText("Queries")).toBeNull()
  })

  test("creators_search_page_seeded_job_stays_visible_on_both_tabs", async () => {
    // Arrange
    const user = userEvent.setup()
    seedCurrentJobs([createDoneJob("job_seed_1")])
    renderCreatorsSearchPage(createBillingSummary())

    // Assert
    expect(screen.getByText("Queries")).toBeVisible()
    expect(screen.getByText("job_seed_1")).toBeVisible()

    // Act
    await user.click(
      screen.getByRole("tab", { name: /Browse by Category or Role/i }),
    )

    // Assert
    expect(
      await screen.findByText("Run a search to explore saved creators."),
    ).toBeVisible()
    expect(screen.getByText("job_seed_1")).toBeVisible()
  })

  test("creators_search_page_multiple_jobs_view_all_opens_jobs_dialog", async () => {
    // Arrange
    const user = userEvent.setup()
    seedCurrentJobs([
      createDoneJob("job_newest"),
      createDoneJob("job_older", ["beta"]),
    ])
    renderCreatorsSearchPage(createBillingSummary())
    expect(screen.queryByText("job_older")).toBeNull()

    // Act
    await user.click(screen.getByRole("button", { name: "View all (2)" }))

    // Assert
    expect(await screen.findByText("2 / 10 jobs")).toBeVisible()
    expect(screen.getByText("job_older")).toBeVisible()
  })

  test("creators_search_page_job_card_click_opens_detail_and_reuse_fills_usernames", async () => {
    // Arrange
    const user = userEvent.setup()
    seedCurrentJobs([createDoneJob("job_seed_1", ["alpha", "beta"])])
    renderCreatorsSearchPage(createBillingSummary())

    // Act
    await user.click(screen.getByText("job_seed_1"))

    // Assert
    expect(await screen.findByText("CURRENT JOB DETAIL")).toBeVisible()

    // Act: reuse the ready usernames from the detail dialog.
    await user.click(screen.getByRole("button", { name: "Search" }))

    // Assert
    expect(screen.getByTestId("tab-usernames")).toHaveTextContent("alpha beta")
    await waitFor(() =>
      expect(screen.queryByText("CURRENT JOB DETAIL")).toBeNull(),
    )
  })

  test("creators_search_page_history_button_opens_history_dialog", async () => {
    // Arrange
    const user = userEvent.setup()
    listCreatorsSearchHistoryMock.mockResolvedValue({ items: [] })
    renderCreatorsSearchPage(createBillingSummary())

    // Act
    await user.click(
      await screen.findByRole("button", { name: "open history from tab" }),
    )

    // Assert
    expect(await screen.findByText("Search history")).toBeVisible()
    expect(
      await screen.findByText("No search history available yet."),
    ).toBeVisible()
    expect(listCreatorsSearchHistoryMock).toHaveBeenCalledWith({ limit: 20 })
  })
})
