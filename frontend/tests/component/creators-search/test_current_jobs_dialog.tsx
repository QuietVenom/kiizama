import { screen } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import { describe, expect, test, vi } from "vitest"

import type { CreatorsSearchLocalJob } from "../../../src/lib/creators-search-jobs"
import { CurrentJobsDialog } from "../../../src/routes/_layout/-components/creators-search/CurrentJobsDialog"
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

describe("current jobs dialog", () => {
  test("current_jobs_dialog_open_renders_all_jobs_and_count", () => {
    // Arrange / Act
    renderWithProviders(
      <CurrentJobsDialog
        jobs={[
          createJob({ jobId: "job_newest" }),
          createJob({ jobId: "job_older" }),
        ]}
        open
        onOpenChange={vi.fn()}
        onSelectJob={vi.fn()}
      />,
    )

    // Assert
    expect(screen.getByText("job_newest")).toBeVisible()
    expect(screen.getByText("job_older")).toBeVisible()
    expect(screen.getByText("2 / 10 trabajos")).toBeVisible()
  })

  test("current_jobs_dialog_done_job_click_calls_select_job", async () => {
    // Arrange
    const user = userEvent.setup()
    const onSelectJob = vi.fn()
    renderWithProviders(
      <CurrentJobsDialog
        jobs={[
          createJob({
            readyUsernames: ["alpha"],
            status: "done",
          }),
        ]}
        open
        onOpenChange={vi.fn()}
        onSelectJob={onSelectJob}
      />,
    )

    // Act
    await user.click(screen.getByText("job_123"))

    // Assert
    expect(onSelectJob).toHaveBeenCalledWith("job_123")
  })

  test("current_jobs_dialog_close_button_calls_open_change", async () => {
    // Arrange
    const user = userEvent.setup()
    const onOpenChange = vi.fn()
    renderWithProviders(
      <CurrentJobsDialog
        jobs={[createJob()]}
        open
        onOpenChange={onOpenChange}
        onSelectJob={vi.fn()}
      />,
    )

    // Act
    await user.click(screen.getByRole("button", { name: "Cerrar" }))

    // Assert
    expect(onOpenChange).toHaveBeenCalledWith(false)
  })

  test("current_jobs_dialog_empty_list_renders_empty_state", () => {
    // Arrange / Act
    renderWithProviders(
      <CurrentJobsDialog
        jobs={[]}
        open
        onOpenChange={vi.fn()}
        onSelectJob={vi.fn()}
      />,
    )

    // Assert
    expect(screen.getByText("Todavía no hay jobs de scraping.")).toBeVisible()
  })
})
