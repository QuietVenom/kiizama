import { screen } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import { describe, expect, test, vi } from "vitest"

import type { CreatorsSearchLocalJob } from "../../../src/lib/creators-search-jobs"
import { CurrentJobsPanel } from "../../../src/routes/_layout/-components/creators-search/CurrentJobsPanel"
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

describe("current jobs panel", () => {
  test("current_jobs_panel_empty_state_renders_no_jobs_message", () => {
    // Arrange / Act
    renderWithProviders(
      <CurrentJobsPanel currentJobs={[]} onSelectJob={vi.fn()} />,
    )

    // Assert
    expect(screen.getByText("No scrape jobs yet.")).toBeVisible()
    expect(screen.getByText("0 / 10 jobs")).toBeVisible()
  })

  test("current_jobs_panel_queued_job_renders_waiting_progress", () => {
    // Arrange / Act
    renderWithProviders(
      <CurrentJobsPanel currentJobs={[createJob()]} onSelectJob={vi.fn()} />,
    )

    // Assert
    expect(screen.getByText("job_123")).toBeVisible()
    expect(screen.getByText("Queued")).toBeVisible()
    expect(screen.getByText("Waiting for completion.")).toBeVisible()
  })

  test("current_jobs_panel_done_job_click_calls_select_job", async () => {
    // Arrange
    const user = userEvent.setup()
    const onSelectJob = vi.fn()
    renderWithProviders(
      <CurrentJobsPanel
        currentJobs={[
          createJob({
            readyUsernames: ["alpha"],
            status: "done",
          }),
        ]}
        onSelectJob={onSelectJob}
      />,
    )

    // Act
    await user.click(screen.getByText("job_123"))

    // Assert
    expect(onSelectJob).toHaveBeenCalledWith("job_123")
  })
})
