import { afterEach, beforeEach, describe, expect, test, vi } from "vitest"

import { UsersService } from "../../../../src/client"
import {
  clearStoredAccessToken,
  ensureValidStoredSession,
  getStoredAccessToken,
  hasStoredAccessToken,
  setStoredAccessToken,
} from "../../../../src/features/auth/session"

describe("auth session storage", () => {
  beforeEach(() => {
    localStorage.clear()
  })

  afterEach(() => {
    vi.restoreAllMocks()
  })

  test("session_without_stored_token_returns_false_without_api_call", async () => {
    // Arrange
    const readUserMe = vi
      .spyOn(UsersService, "readUserMe")
      .mockRejectedValue(new Error("should not be called"))

    // Act
    const isValid = await ensureValidStoredSession()

    // Assert
    expect(isValid).toBe(false)
    expect(readUserMe).not.toHaveBeenCalled()
  })

  test("session_valid_stored_token_keeps_token_after_successful_validation", async () => {
    // Arrange
    setStoredAccessToken("valid-token")
    vi.spyOn(UsersService, "readUserMe").mockResolvedValue({
      id: "user-1",
    } as never)

    // Act
    const isValid = await ensureValidStoredSession()

    // Assert
    expect(isValid).toBe(true)
    expect(hasStoredAccessToken()).toBe(true)
    expect(getStoredAccessToken()).toBe("valid-token")
  })

  test("session_expired_stored_token_clears_storage_after_api_failure", async () => {
    // Arrange
    setStoredAccessToken("expired-token")
    vi.spyOn(UsersService, "readUserMe").mockRejectedValue(
      new Error("Unauthorized"),
    )

    // Act
    const isValid = await ensureValidStoredSession()

    // Assert
    expect(isValid).toBe(false)
    expect(hasStoredAccessToken()).toBe(false)
    expect(getStoredAccessToken()).toBeNull()
  })

  test("session_corrupted_storage_value_is_removed_when_validation_fails", async () => {
    // Arrange
    localStorage.setItem("access_token", "{not-json")
    vi.spyOn(UsersService, "readUserMe").mockRejectedValue(
      new Error("Invalid token"),
    )

    // Act
    const isValid = await ensureValidStoredSession()

    // Assert
    expect(isValid).toBe(false)
    expect(getStoredAccessToken()).toBeNull()
  })

  test("session_clear_stored_access_token_removes_existing_token", () => {
    // Arrange
    setStoredAccessToken("second-token")

    // Act
    clearStoredAccessToken()

    // Assert
    expect(hasStoredAccessToken()).toBe(false)
  })
})
