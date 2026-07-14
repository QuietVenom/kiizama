import { beforeEach, describe, expect, test } from "vitest"

import { buildCompletedDescription } from "../../../../src/features/user-events/toast-descriptions"
import type {
  IgScrapeTerminalEventCounters,
  IgScrapeTerminalEventPayload,
} from "../../../../src/features/user-events/types"
import i18n from "../../../../src/i18n"

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

describe("user event toast descriptions", () => {
  beforeEach(async () => {
    await i18n.changeLanguage("en")
  })

  test("toast_description_spanish_language_localizes_ready_count", async () => {
    // Arrange
    await i18n.changeLanguage("es")

    // Act
    const description = buildCompletedDescription(createPayload())

    // Assert
    expect(description).toBe("1 de 3 usernames están listos.")
  })

  test("toast_description_skipped_ready_usernames_count_as_ready", () => {
    // Arrange / Act
    const description = buildCompletedDescription(
      createPayload({
        ready_usernames: ["alpha", "beta", "gamma"],
        successful_usernames: ["alpha"],
        skipped_usernames: ["beta", "gamma"],
        counters: createCounters({ requested: 3, successful: 1 }),
      }),
    )

    // Assert
    expect(description).toBe("3 of 3 usernames are ready.")
  })

  test("toast_description_single_ready_username_uses_requested_count", () => {
    // Arrange / Act
    const description = buildCompletedDescription(
      createPayload({
        ready_usernames: ["alpha"],
        successful_usernames: ["alpha"],
        skipped_usernames: [],
        counters: createCounters({ requested: 3, successful: 1 }),
      }),
    )

    // Assert
    expect(description).toBe("1 of 3 usernames are ready.")
  })

  test("toast_description_zero_requested_usernames_uses_generic_fallback", () => {
    // Arrange / Act
    const description = buildCompletedDescription(
      createPayload({
        requested_usernames: [],
        ready_usernames: [],
        successful_usernames: [],
        counters: createCounters({ requested: 0, successful: 0 }),
      }),
    )

    // Assert
    expect(description).toBe("The Instagram scrape job completed successfully.")
  })

  test("toast_description_partial_failure_still_uses_ready_count", () => {
    // Arrange / Act
    const description = buildCompletedDescription(
      createPayload({
        ready_usernames: ["alpha", "beta"],
        failed_usernames: ["gamma"],
        counters: createCounters({ requested: 3, successful: 2, failed: 1 }),
      }),
    )

    // Assert
    expect(description).toBe("2 of 3 usernames are ready.")
  })
})
