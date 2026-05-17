import { describe, expect, test } from "vitest"

import {
  isValidInstagramUsername,
  MAX_INSTAGRAM_USERNAMES,
  normalizeInstagramUsername,
  parseInstagramUsernamesInput,
  sanitizeInstagramUsernames,
} from "../../../src/lib/instagram-usernames"

describe("instagram usernames", () => {
  test("instagram_username_normalize_removes_at_trims_and_lowercases", () => {
    // Arrange / Act
    const username = normalizeInstagramUsername("  @User.Name  ")

    // Assert
    expect(username).toBe("user.name")
  })

  test("instagram_username_normalize_extracts_username_from_instagram_profile_urls", () => {
    // Arrange / Act / Assert
    expect(
      normalizeInstagramUsername("https://www.instagram.com/emilio.marcos/"),
    ).toBe("emilio.marcos")
    expect(
      normalizeInstagramUsername("https://www.instagram.com/emilio.marcos"),
    ).toBe("emilio.marcos")
    expect(
      normalizeInstagramUsername("http://www.instagram.com/emilio.marcos"),
    ).toBe("emilio.marcos")
    expect(
      normalizeInstagramUsername("https://instagram.com/emilio.marcos"),
    ).toBe("emilio.marcos")
    expect(
      normalizeInstagramUsername(
        "https://www.instagram.com/emilio.marcos/?hl=en",
      ),
    ).toBe("emilio.marcos")
    expect(
      normalizeInstagramUsername(
        "https://www.instagram.com/emilio.marcos/reels/",
      ),
    ).toBe("emilio.marcos")
  })

  test("instagram_username_normalize_rejects_reserved_or_non_instagram_urls", () => {
    // Arrange / Act / Assert
    expect(
      normalizeInstagramUsername("https://www.instagram.com/p/abc123/"),
    ).toBe("https://www.instagram.com/p/abc123/")
    expect(
      normalizeInstagramUsername("https://www.instagram.com/explore/topics/1"),
    ).toBe("https://www.instagram.com/explore/topics/1")
    expect(normalizeInstagramUsername("https://www.tiktok.com/@emilio")).toBe(
      "https://www.tiktok.com/@emilio",
    )
    expect(normalizeInstagramUsername("https://www.instagram.com/")).toBe(
      "https://www.instagram.com/",
    )
  })

  test("instagram_username_parse_splits_common_separators_and_dedupes", () => {
    // Arrange / Act
    const usernames = parseInstagramUsernamesInput(
      " @Alpha.One, beta_two\nalpha.one   Gamma.Three ",
    )

    // Assert
    expect(usernames).toEqual(["alpha.one", "beta_two", "gamma.three"])
  })

  test("instagram_username_sanitize_preserves_first_normalized_order", () => {
    // Arrange / Act
    const usernames = sanitizeInstagramUsernames([
      "@first",
      "@second",
      "FIRST",
      "third",
    ])

    // Assert
    expect(usernames).toEqual(["first", "second", "third"])
  })

  test("instagram_username_sanitize_dedupes_mixed_handles_and_profile_urls", () => {
    // Arrange / Act
    const usernames = sanitizeInstagramUsernames([
      "@emilio.marcos",
      "https://www.instagram.com/emilio.marcos/",
      "instagram.com/Emilio.Marcos",
      "second_creator",
    ])

    // Assert
    expect(usernames).toEqual(["emilio.marcos", "second_creator"])
  })

  test("instagram_username_validation_rejects_invalid_shapes", () => {
    // Arrange / Act / Assert
    expect(isValidInstagramUsername("valid.user_1")).toBe(true)
    expect(isValidInstagramUsername("double..dot")).toBe(false)
    expect(isValidInstagramUsername(".starts_with_dot")).toBe(false)
    expect(isValidInstagramUsername("ends_with_dot.")).toBe(false)
    expect(isValidInstagramUsername("bad-char!")).toBe(false)
    expect(isValidInstagramUsername("a".repeat(31))).toBe(false)
  })

  test("instagram_username_parse_caps_result_to_max_list", () => {
    // Arrange
    const input = Array.from(
      { length: MAX_INSTAGRAM_USERNAMES + 5 },
      (_, index) => `user_${index}`,
    ).join(",")

    // Act
    const usernames = parseInstagramUsernamesInput(input)

    // Assert
    expect(usernames).toHaveLength(MAX_INSTAGRAM_USERNAMES)
    expect(usernames[0]).toBe("user_0")
    expect(usernames[usernames.length - 1]).toBe(
      `user_${MAX_INSTAGRAM_USERNAMES - 1}`,
    )
  })
})
