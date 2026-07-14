import { screen } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import { describe, expect, test, vi } from "vitest"

import type { CreatorsSearchLocalJob } from "../../../src/lib/creators-search-jobs"
import { CurrentJobsSummary } from "../../../src/routes/_layout/-components/creators-search/CurrentJobsSummary"
import { renderWithProviders } from "../helpers/render"

const createJob = (
  overrides: Partial<CreatorsSearchLocalJob> = {},
): CreatorsSearchLocalJob => ({
  batchKey: "missing:alpha",
  createdAt: "2026-01-01T00:00:00Z",
  error: null,
  jobId: "job_123",
  readyUsernames: [],
  requestedUsernames: ["alpha"],
  sourceBox: "missing",
  status: "queued",
  terminalPayload: null,
  updatedAt: "2026-01-01T00:00:00Z",
  ...overrides,
})

describe("current jobs summary", () => {
  test("current_jobs_summary_empty_list_renders_nothing", () => {
    // Arrange / Act
    renderWithProviders(
      <CurrentJobsSummary
        currentJobs={[]}
        onSelectJob={vi.fn()}
        onViewAll={vi.fn()}
      />,
    )

    // Assert
    expect(screen.queryByText("Consultas")).toBeNull()
  })

  test("current_jobs_summary_single_job_renders_latest_without_view_all", () => {
    // Arrange / Act
    renderWithProviders(
      <CurrentJobsSummary
        currentJobs={[createJob()]}
        onSelectJob={vi.fn()}
        onViewAll={vi.fn()}
      />,
    )

    // Assert
    expect(screen.getByText("Consultas")).toBeVisible()
    expect(screen.getByText("job_123")).toBeVisible()
    expect(screen.getByText("En cola")).toBeVisible()
    expect(screen.getByText("Consultas: 1")).toBeVisible()
    expect(screen.queryByText(/Ver todo/)).toBeNull()
  })

  test("current_jobs_summary_multiple_jobs_renders_only_newest_and_view_all", async () => {
    // Arrange
    const user = userEvent.setup()
    const onViewAll = vi.fn()
    renderWithProviders(
      <CurrentJobsSummary
        currentJobs={[
          createJob({ jobId: "job_newest" }),
          createJob({ jobId: "job_older" }),
        ]}
        onSelectJob={vi.fn()}
        onViewAll={onViewAll}
      />,
    )

    // Assert
    expect(screen.getByText("job_newest")).toBeVisible()
    expect(screen.queryByText("job_older")).toBeNull()

    // Act
    await user.click(screen.getByRole("button", { name: "Ver todo (2)" }))

    // Assert
    expect(onViewAll).toHaveBeenCalledTimes(1)
  })

  test("current_jobs_summary_done_job_click_calls_select_job", async () => {
    // Arrange
    const user = userEvent.setup()
    const onSelectJob = vi.fn()
    renderWithProviders(
      <CurrentJobsSummary
        currentJobs={[
          createJob({
            readyUsernames: ["alpha"],
            status: "done",
          }),
        ]}
        onSelectJob={onSelectJob}
        onViewAll={vi.fn()}
      />,
    )

    // Act
    await user.click(screen.getByText("job_123"))

    // Assert
    expect(onSelectJob).toHaveBeenCalledWith("job_123")
  })
})
