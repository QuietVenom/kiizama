import { afterEach, describe, expect, test, vi } from "vitest"

import {
  applyUserEventEffects,
  registerUserEventEffect,
} from "../../../../src/features/user-events/effects"
import type { UserEvent } from "../../../../src/features/user-events/types"

const createEvent = (name = "custom.event"): UserEvent => ({
  envelope: {
    kind: "notification",
    notification_id: "notification-1",
    payload: {},
    source: "tests",
    topic: "tests",
  },
  id: "event-1",
  name,
})

describe("user event effects", () => {
  const cleanupCallbacks: Array<() => void> = []

  afterEach(() => {
    while (cleanupCallbacks.length > 0) {
      cleanupCallbacks.pop()?.()
    }
    vi.restoreAllMocks()
  })

  test("user_event_effects_registered_effect_receives_dispatched_event", () => {
    // Arrange
    const effect = vi.fn()
    cleanupCallbacks.push(registerUserEventEffect(effect))
    const event = createEvent()

    // Act
    applyUserEventEffects(event)

    // Assert
    expect(effect).toHaveBeenCalledWith(event)
  })

  test("user_event_effects_unsubscribe_prevents_future_dispatches", () => {
    // Arrange
    const effect = vi.fn()
    const unsubscribe = registerUserEventEffect(effect)
    unsubscribe()

    // Act
    applyUserEventEffects(createEvent())

    // Assert
    expect(effect).not.toHaveBeenCalled()
  })

  test("user_event_effects_failed_effect_does_not_block_remaining_effects", () => {
    // Arrange
    const consoleError = vi
      .spyOn(console, "error")
      .mockImplementation(() => undefined)
    const failedEffect = vi.fn(() => {
      throw new Error("boom")
    })
    const successfulEffect = vi.fn()
    cleanupCallbacks.push(registerUserEventEffect(failedEffect))
    cleanupCallbacks.push(registerUserEventEffect(successfulEffect))
    const event = createEvent()

    // Act
    applyUserEventEffects(event)

    // Assert
    expect(successfulEffect).toHaveBeenCalledWith(event)
    expect(consoleError).toHaveBeenCalledWith(
      "User event effect failed.",
      expect.any(Error),
    )
  })
})
