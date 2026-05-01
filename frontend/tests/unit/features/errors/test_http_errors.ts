import { describe, expect, test } from "vitest"

import { ApiError } from "../../../../src/client/core/ApiError"
import {
  isHandledStatus,
  isRetryableStatus,
  normalizeAppError,
  rethrowCriticalQueryError,
} from "../../../../src/features/errors/http"

const createApiError = (status: number, detail?: unknown) =>
  new ApiError(
    {
      method: "GET",
      url: "/api/test",
    } as never,
    {
      body: detail === undefined ? undefined : { detail },
      ok: false,
      status,
      statusText: "Error",
      url: "/api/test",
    },
    typeof detail === "string" ? detail : "Error",
  )

describe("HTTP error normalization", () => {
  test("http_errors_handled_api_status_codes_normalize_to_app_error", () => {
    // Arrange / Act / Assert
    expect(normalizeAppError(createApiError(401), "mutation")).toMatchObject({
      status: 401,
      retryable: false,
    })
    expect(normalizeAppError(createApiError(403), "loader")).toMatchObject({
      status: 403,
      retryable: false,
    })
    expect(normalizeAppError(createApiError(404), "router")).toMatchObject({
      status: 404,
      retryable: false,
    })
    expect(normalizeAppError(createApiError(500), "query")).toMatchObject({
      status: 500,
      retryable: true,
    })
    expect(normalizeAppError(createApiError(503), "query")).toMatchObject({
      status: 503,
      retryable: true,
    })
  })

  test("http_errors_unknown_errors_map_to_retryable_500", () => {
    // Arrange / Act
    const normalizedUnknownError = normalizeAppError(
      new Error("Unexpected failure"),
      "unknown",
    )

    // Assert
    expect(normalizedUnknownError).toMatchObject({
      status: 500,
      message: "Unexpected failure",
      retryable: true,
    })
    expect(isRetryableStatus(500)).toBe(true)
    expect(isRetryableStatus(503)).toBe(true)
    expect(isRetryableStatus(403)).toBe(false)
    expect(isHandledStatus(404)).toBe(true)
    expect(isHandledStatus(418)).toBe(false)
  })

  test("http_errors_detail_array_uses_first_message", () => {
    // Arrange / Act
    const normalized = normalizeAppError(
      createApiError(422, [{ msg: "Invalid payload" }]),
      "mutation",
    )

    // Assert
    expect(normalized.status).toBe(500)
    expect(normalized.message).toBe("Invalid payload")
  })

  test("http_errors_missing_detail_uses_fallback_message", () => {
    // Arrange / Act
    const normalized = normalizeAppError(createApiError(503), "query")

    // Assert
    expect(normalized.status).toBe(503)
    expect(normalized.message).toBe("Error")
  })

  test("http_errors_critical_query_statuses_are_rethrown", () => {
    // Arrange / Act / Assert
    for (const status of [403, 500, 503]) {
      try {
        rethrowCriticalQueryError(createApiError(status), "query")
        throw new Error("Expected critical query error to be rethrown")
      } catch (error) {
        expect(error).toMatchObject({ status })
      }
    }
  })

  test("http_errors_401_and_empty_query_errors_are_not_rethrown", () => {
    // Arrange / Act / Assert
    expect(() => rethrowCriticalQueryError(undefined, "query")).not.toThrow()
    expect(() =>
      rethrowCriticalQueryError(createApiError(401), "query"),
    ).not.toThrow()
  })
})
