import { beforeEach, describe, expect, test, vi } from "vitest"

import type {
  IgScrapeTerminalEventPayload,
  UserEvent,
} from "../../../../src/features/user-events/types"

const { effects, toaster } = vi.hoisted(() => ({
  effects: {
    registerUserEventEffect: vi.fn(),
  },
  toaster: {
    create: vi.fn(),
  },
}))

vi.mock("@/components/ui/toaster", () => ({
  toaster,
}))

vi.mock("@/features/user-events/effects", () => ({
  registerUserEventEffect: effects.registerUserEventEffect,
}))

const { registerToastUserEventEffects } = await import(
  "../../../../src/features/user-events/toast-effects"
)

const createTerminalPayload = (
  overrides: Partial<IgScrapeTerminalEventPayload> = {},
): IgScrapeTerminalEventPayload => ({
  completed_at: "2026-01-01T00:01:00Z",
  counters: {
    failed: 0,
    not_found: 0,
    requested: 2,
    successful: 1,
  },
  created_at: "2026-01-01T00:00:00Z",
  error: null,
  event_version: 1,
  failed_usernames: [],
  job_id: "job-1",
  not_found_usernames: [],
  notification_id: "notification-1",
  ready_usernames: ["alpha", "beta"],
  requested_usernames: ["alpha", "beta"],
  skipped_usernames: ["beta"],
  status: "done",
  successful_usernames: ["alpha"],
  ...overrides,
})

const createEvent = (
  name: UserEvent["name"],
  payload: IgScrapeTerminalEventPayload | Record<string, unknown>,
): UserEvent =>
  ({
    envelope: {
      kind: "notification",
      notification_id: "notification-1",
      payload,
      source: "tests",
      topic: "tests",
    },
    id: "event-1",
    name,
  }) as UserEvent

describe("user event toast effects", () => {
  beforeEach(() => {
    effects.registerUserEventEffect.mockReset()
    toaster.create.mockClear()
  })

  test("toast_effects_completed_job_creates_success_toast", () => {
    // Arrange
    registerToastUserEventEffects()
    const effect = effects.registerUserEventEffect.mock.calls[0][0]

    // Act
    effect(createEvent("ig-scrape.job.completed", createTerminalPayload()))

    // Assert
    expect(toaster.create).toHaveBeenCalledWith(
      expect.objectContaining({
        description: "2 of 2 usernames are ready.",
        title: "Scrape completed",
        type: "success",
      }),
    )
  })

  test("toast_effects_failed_job_creates_error_toast_with_payload_error", () => {
    // Arrange
    registerToastUserEventEffects()
    const effect = effects.registerUserEventEffect.mock.calls[0][0]

    // Act
    effect(
      createEvent(
        "ig-scrape.job.failed",
        createTerminalPayload({
          error: "Worker failed.",
          status: "failed",
        }),
      ),
    )

    // Assert
    expect(toaster.create).toHaveBeenCalledWith(
      expect.objectContaining({
        description: "Worker failed.",
        title: "Scrape failed",
        type: "error",
      }),
    )
  })

  test("toast_effects_non_scrape_event_does_not_create_toast", () => {
    // Arrange
    registerToastUserEventEffects()
    const effect = effects.registerUserEventEffect.mock.calls[0][0]

    // Act
    effect(createEvent("account.usage.updated", {}))

    // Assert
    expect(toaster.create).not.toHaveBeenCalled()
  })
})
