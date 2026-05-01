import { beforeEach, describe, expect, test, vi } from "vitest"
import type { InstagramScrapeJobStatusResponse } from "@/client"

import type { CreatorsSearchLocalJob } from "../../../src/lib/creators-search-jobs"
import {
  buildCreatorsSearchBatchKey,
  buildTerminalPayloadFromJobStatus,
  CREATORS_SEARCH_JOBS_STORAGE_KEY,
  createBalancedUsernameBatches,
  getCreatorsSearchJobProgressText,
  getCreatorsSearchJobStatusLabel,
  MAX_CREATORS_SEARCH_JOBS,
  readCreatorsSearchJobs,
  syncLocalJobWithStatusResponse,
  upsertCreatorsSearchJob,
} from "../../../src/lib/creators-search-jobs"

const createJob = (
  overrides: Partial<CreatorsSearchLocalJob> = {},
): CreatorsSearchLocalJob => ({
  batchKey: "missing:alpha,beta",
  createdAt: "2026-01-01T00:00:00Z",
  error: null,
  jobId: "job-1",
  readyUsernames: [],
  requestedUsernames: ["alpha", "beta"],
  sourceBox: "missing",
  status: "queued",
  terminalPayload: null,
  updatedAt: "2026-01-01T00:00:00Z",
  ...overrides,
})

const createStatusResponse = (
  overrides: Partial<InstagramScrapeJobStatusResponse> = {},
): InstagramScrapeJobStatusResponse => ({
  created_at: "2026-01-01T00:00:00Z",
  error: null,
  expires_at: "2026-01-02T00:00:00Z",
  job_id: "job-1",
  status: "queued",
  updated_at: "2026-01-01T00:01:00Z",
  ...overrides,
})

describe("creators search jobs", () => {
  beforeEach(() => {
    localStorage.clear()
  })

  test("creators_search_jobs_corrupt_storage_returns_empty_list", () => {
    // Arrange
    localStorage.setItem(CREATORS_SEARCH_JOBS_STORAGE_KEY, "{not-json")

    // Act / Assert
    expect(readCreatorsSearchJobs()).toEqual([])
  })

  test("creators_search_jobs_upsert_replaces_existing_and_trims_to_max", () => {
    // Arrange
    const dispatchEvent = vi.spyOn(window, "dispatchEvent")
    for (let index = 0; index < MAX_CREATORS_SEARCH_JOBS + 2; index += 1) {
      upsertCreatorsSearchJob(
        createJob({
          jobId: `job-${index}`,
          updatedAt: `2026-01-01T00:${String(index).padStart(2, "0")}:00Z`,
        }),
      )
    }

    // Act
    const jobs = upsertCreatorsSearchJob(
      createJob({
        jobId: "job-5",
        readyUsernames: ["updated"],
        status: "done",
      }),
    )

    // Assert
    expect(jobs).toHaveLength(MAX_CREATORS_SEARCH_JOBS)
    expect(jobs[0]).toMatchObject({
      jobId: "job-5",
      readyUsernames: ["updated"],
      status: "done",
    })
    expect(jobs.filter((job) => job.jobId === "job-5")).toHaveLength(1)
    expect(dispatchEvent).toHaveBeenCalled()
  })

  test("creators_search_batch_key_dedupes_and_sorts_by_source_box", () => {
    // Arrange / Act
    const key = buildCreatorsSearchBatchKey("expired", [
      "beta",
      "alpha",
      "beta",
    ])

    // Assert
    expect(key).toBe("expired:alpha,beta")
  })

  test("creators_search_balanced_batches_respect_max_batch_size", () => {
    // Arrange
    const usernames = Array.from({ length: 23 }, (_, index) => `user_${index}`)

    // Act
    const batches = createBalancedUsernameBatches(usernames, 10)

    // Assert
    expect(batches).toHaveLength(3)
    expect(batches.map((batch) => batch.length)).toEqual([8, 8, 7])
    expect(batches.flat()).toEqual(usernames)
  })

  test("creators_search_terminal_payload_prefers_summary_usernames", () => {
    // Arrange
    const response = createStatusResponse({
      status: "done",
      summary: {
        counters: {
          failed: 1,
          not_found: 1,
          requested: 4,
          successful: 1,
        },
        usernames: [
          { status: "success", username: "ready" },
          { status: "skipped", username: "skipped" },
          { status: "failed", username: "failed" },
          { status: "not_found", username: "missing" },
        ],
      },
    })

    // Act
    const payload = buildTerminalPayloadFromJobStatus(response, ["fallback"])

    // Assert
    expect(payload).toMatchObject({
      job_id: "job-1",
      ready_usernames: ["ready", "skipped"],
      requested_usernames: ["ready", "skipped", "failed", "missing"],
      status: "done",
    })
  })

  test("creators_search_terminal_payload_uses_references_when_summary_missing", () => {
    // Arrange
    const response = createStatusResponse({
      references: {
        all_usernames: ["alpha", "beta"],
        failed_usernames: ["beta"],
        skipped_usernames: ["alpha"],
      },
      status: "failed",
    })

    // Act
    const payload = buildTerminalPayloadFromJobStatus(response, ["fallback"])

    // Assert
    expect(payload).toMatchObject({
      failed_usernames: ["beta"],
      ready_usernames: ["alpha"],
      requested_usernames: ["alpha", "beta"],
      skipped_usernames: ["alpha"],
      status: "failed",
    })
  })

  test("creators_search_sync_status_maps_non_terminal_to_queued_and_terminal_to_done", () => {
    // Arrange
    const job = createJob()

    // Act
    const runningJob = syncLocalJobWithStatusResponse(
      job,
      createStatusResponse({
        status: "running",
        summary: {
          usernames: [{ status: "success", username: "alpha" }],
        },
      }),
    )
    const doneJob = syncLocalJobWithStatusResponse(
      job,
      createStatusResponse({
        status: "done",
        summary: {
          usernames: [{ status: "skipped", username: "beta" }],
        },
      }),
    )

    // Assert
    expect(runningJob).toMatchObject({
      readyUsernames: ["alpha"],
      status: "queued",
      terminalPayload: null,
    })
    expect(doneJob.status).toBe("done")
    expect(doneJob.terminalPayload?.ready_usernames).toEqual(["beta"])
  })

  test("creators_search_job_status_label_and_progress_text_match_ui_contract", () => {
    // Arrange / Act / Assert
    expect(getCreatorsSearchJobStatusLabel("queued")).toBe("Queued")
    expect(getCreatorsSearchJobStatusLabel("running")).toBe("Queued")
    expect(getCreatorsSearchJobStatusLabel("done")).toBe("Done")
    expect(getCreatorsSearchJobStatusLabel("failed")).toBe("Failed")
    expect(getCreatorsSearchJobProgressText({ canOpenDetail: false })).toBe(
      "Waiting for completion.",
    )
    expect(getCreatorsSearchJobProgressText({ canOpenDetail: true })).toBe(
      "Click to review the terminal result.",
    )
  })
})
