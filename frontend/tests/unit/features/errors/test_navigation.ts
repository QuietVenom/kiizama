import { beforeEach, describe, expect, test } from "vitest"

import {
  buildLoginHrefWithReturnTo,
  getCurrentPathWithSearchAndHash,
  getReturnToFromHref,
  sanitizeReturnTo,
} from "../../../../src/features/errors/navigation"

describe("error navigation helpers", () => {
  beforeEach(() => {
    localStorage.clear()
    window.history.replaceState(null, "", "/")
  })

  test("navigation_safe_internal_return_to_values_are_preserved", () => {
    // Arrange / Act / Assert
    expect(sanitizeReturnTo("/brand-intelligence")).toBe("/brand-intelligence")
    expect(sanitizeReturnTo("/overview?tab=reports#latest")).toBe(
      "/overview?tab=reports#latest",
    )
    expect(getReturnToFromHref("/login?redirect=%2Fsettings")).toBe("/settings")
  })

  test("navigation_malicious_or_login_return_to_values_fall_back_to_login", () => {
    // Arrange / Act / Assert
    expect(sanitizeReturnTo("https://evil.example")).toBeUndefined()
    expect(sanitizeReturnTo("//evil.example")).toBeUndefined()
    expect(sanitizeReturnTo("")).toBeUndefined()
    expect(buildLoginHrefWithReturnTo("https://evil.example")).toBe("/login")
    expect(buildLoginHrefWithReturnTo("//evil.example")).toBe("/login")
    expect(buildLoginHrefWithReturnTo("/login?redirect=%2Fsettings")).toBe(
      "/login",
    )
  })

  test("navigation_valid_return_to_builds_encoded_login_href", () => {
    // Arrange / Act / Assert
    expect(buildLoginHrefWithReturnTo("/overview?tab=reports")).toBe(
      "/login?redirect=%2Foverview%3Ftab%3Dreports",
    )
  })

  test("navigation_current_path_includes_search_and_hash", () => {
    // Arrange
    window.history.replaceState(null, "", "/settings?tab=profile#name")

    // Act / Assert
    expect(getCurrentPathWithSearchAndHash()).toBe("/settings?tab=profile#name")
  })

  test("navigation_login_href_with_return_to_is_safe_for_redirect_callers", () => {
    // Arrange / Act / Assert
    expect(buildLoginHrefWithReturnTo("/overview")).toBe(
      "/login?redirect=%2Foverview",
    )
  })
})
