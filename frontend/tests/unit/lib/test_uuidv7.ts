import { describe, expect, test, vi } from "vitest"

import { uuidv7 } from "../../../src/lib/uuidv7"

const UUID_PATTERN =
  /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/

describe("uuidv7", () => {
  test("uuidv7_generated_id_matches_canonical_format", () => {
    // Arrange / Act
    const id = uuidv7()

    // Assert
    expect(id).toMatch(UUID_PATTERN)
  })

  test("uuidv7_version_nibble_is_seven_and_variant_is_rfc", () => {
    // Arrange / Act
    const id = uuidv7()

    // Assert: version nibble is the first hex digit of the third group.
    expect(id[14]).toBe("7")
    // Variant bits 10xx → first hex digit of the fourth group in [8, 9, a, b].
    expect(["8", "9", "a", "b"]).toContain(id[19])
  })

  test("uuidv7_batch_generates_unique_ids", () => {
    // Arrange / Act
    const ids = new Set(Array.from({ length: 500 }, () => uuidv7()))

    // Assert
    expect(ids.size).toBe(500)
  })

  test("uuidv7_ids_sort_by_generation_time", () => {
    // Arrange
    vi.useFakeTimers()
    try {
      vi.setSystemTime(new Date("2026-07-07T00:00:00Z"))
      const earlier = uuidv7()
      vi.setSystemTime(new Date("2026-07-07T00:00:01Z"))
      const later = uuidv7()

      // Act / Assert: timestamp prefix makes ids lexicographically sortable.
      expect(earlier < later).toBe(true)
    } finally {
      vi.useRealTimers()
    }
  })
})
