import assert from "node:assert/strict"
import test from "node:test"

import { buildCompletedDescription } from "../src/features/user-events/toast-descriptions.ts"
import type {
  IgScrapeTerminalEventCounters,
  IgScrapeTerminalEventPayload,
} from "../src/features/user-events/types.ts"

const createCounters = (
  overrides: Partial<IgScrapeTerminalEventCounters> = {},
): IgScrapeTerminalEventCounters => ({
  requested: 3,
  successful: 1,
  failed: 0,
  not_found: 0,
  ...overrides,
})

const createPayload = (
  overrides: Partial<IgScrapeTerminalEventPayload> = {},
): IgScrapeTerminalEventPayload => ({
  event_version: 1,
  notification_id: "notification-1",
  job_id: "job-1",
  status: "done",
  created_at: "2026-03-15T00:00:00Z",
  completed_at: "2026-03-15T00:01:00Z",
  requested_usernames: ["alpha", "beta", "gamma"],
  ready_usernames: ["alpha"],
  successful_usernames: ["alpha"],
  skipped_usernames: [],
  failed_usernames: [],
  not_found_usernames: [],
  counters: createCounters(),
  error: null,
  ...overrides,
})

test("uses ready_usernames length for ready copy when skipped usernames are ready", () => {
  const description = buildCompletedDescription(
    createPayload({
      ready_usernames: ["alpha", "beta", "gamma"],
      successful_usernames: ["alpha"],
      skipped_usernames: ["beta", "gamma"],
      counters: createCounters({
        requested: 3,
        successful: 1,
      }),
    }),
  )

  assert.equal(description, "3 of 3 usernames are ready.")
})

test("keeps the ready copy aligned with requested usernames when only one is ready", () => {
  const description = buildCompletedDescription(
    createPayload({
      ready_usernames: ["alpha"],
      successful_usernames: ["alpha"],
      skipped_usernames: [],
      counters: createCounters({
        requested: 3,
        successful: 1,
      }),
    }),
  )

  assert.equal(description, "1 of 3 usernames are ready.")
})

test("keeps the generic fallback when requested usernames is zero", () => {
  const description = buildCompletedDescription(
    createPayload({
      requested_usernames: [],
      ready_usernames: [],
      successful_usernames: [],
      counters: createCounters({
        requested: 0,
        successful: 0,
      }),
    }),
  )

  assert.equal(description, "The Instagram scrape job completed successfully.")
})
