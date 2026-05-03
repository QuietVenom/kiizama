import { describe, expect, test } from "vitest"

import { formatBlogPublishedAt } from "../../../../src/features/blog/format"

describe("blog date formatting", () => {
  test("formats date-only publishedAt in english without shifting the day", () => {
    expect(formatBlogPublishedAt("2026-04-05", "en")).toBe("April 5, 2026")
  })

  test("formats date-only publishedAt in spanish", () => {
    expect(formatBlogPublishedAt("2026-04-05", "es")).toBe("5 de abril de 2026")
  })

  test("formats datetime publishedAt in portuguese", () => {
    expect(formatBlogPublishedAt("2026-04-25T12:00:00Z", "pt-BR")).toBe(
      "25 de abril de 2026",
    )
  })

  test("returns the original value when publishedAt is invalid", () => {
    expect(formatBlogPublishedAt("not-a-date", "es")).toBe("not-a-date")
  })
})
