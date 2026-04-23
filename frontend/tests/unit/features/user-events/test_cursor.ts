import { beforeEach, describe, expect, test, vi } from "vitest"

import {
  clearUserEventsCursor,
  readUserEventsCursor,
  writeUserEventsCursor,
} from "../../../../src/features/user-events/cursor"

const storageKey = (userId: string) => `user-events:last-event-id:${userId}`

describe("user events cursor", () => {
  beforeEach(() => {
    sessionStorage.clear()
    vi.useRealTimers()
  })

  test("user_events_cursor_valid_cursor_is_read", () => {
    // Arrange
    writeUserEventsCursor("user-1", "event-123")

    // Act / Assert
    expect(readUserEventsCursor("user-1")).toBe("event-123")
  })

  test("user_events_cursor_invalid_json_is_removed", () => {
    // Arrange
    sessionStorage.setItem(storageKey("user-1"), "{not-json")

    // Act / Assert
    expect(readUserEventsCursor("user-1")).toBeNull()
    expect(sessionStorage.getItem(storageKey("user-1"))).toBeNull()
  })

  test("user_events_cursor_expired_cursor_is_removed", () => {
    // Arrange
    vi.useFakeTimers()
    vi.setSystemTime(new Date("2026-01-01T00:20:00Z"))
    sessionStorage.setItem(
      storageKey("user-1"),
      JSON.stringify({
        updatedAt: new Date("2026-01-01T00:00:00Z").getTime(),
        value: "event-old",
      }),
    )

    // Act / Assert
    expect(readUserEventsCursor("user-1")).toBeNull()
    expect(sessionStorage.getItem(storageKey("user-1"))).toBeNull()
  })

  test("user_events_cursor_clear_removes_only_matching_user", () => {
    // Arrange
    writeUserEventsCursor("user-1", "event-1")
    writeUserEventsCursor("user-2", "event-2")

    // Act
    clearUserEventsCursor("user-1")

    // Assert
    expect(readUserEventsCursor("user-1")).toBeNull()
    expect(readUserEventsCursor("user-2")).toBe("event-2")
  })
})
