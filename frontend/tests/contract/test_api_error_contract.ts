import { describe, expect, test } from "vitest"

import { ApiError } from "../../src/client"
import {
  normalizeAppError,
  rethrowCriticalQueryError,
} from "../../src/features/errors/http"

describe("API error contract", () => {
  test("api_error_shape_exposes_status_body_url_and_request_for_error_normalization", () => {
    // Arrange
    const error = new ApiError(
      { method: "GET", url: "/api/v1/users/me" } as never,
      {
        body: { detail: "Session expired" },
        ok: false,
        status: 401,
        statusText: "Unauthorized",
        url: "/api/v1/users/me",
      },
      "Session expired",
    )

    // Act
    const normalized = normalizeAppError(error, "query")

    // Assert
    expect(error.name).toBe("ApiError")
    expect(error.status).toBe(401)
    expect(error.url).toBe("/api/v1/users/me")
    expect(error.body).toEqual({ detail: "Session expired" })
    expect(error.request).toMatchObject({
      method: "GET",
      url: "/api/v1/users/me",
    })
    expect(normalized).toMatchObject({
      status: 401,
      message: "Session expired",
      retryable: false,
    })
  })

  test("api_error_validation_detail_array_contract_uses_first_message", () => {
    // Arrange
    const error = new ApiError(
      { method: "POST", url: "/api/v1/users/signup" } as never,
      {
        body: { detail: [{ msg: "Invalid email address" }] },
        ok: false,
        status: 422,
        statusText: "Validation Error",
        url: "/api/v1/users/signup",
      },
      "Validation Error",
    )

    // Act
    const normalized = normalizeAppError(error, "mutation")

    // Assert
    expect(normalized.status).toBe(500)
    expect(normalized.message).toBe("Invalid email address")
  })

  test("api_error_string_detail_contract_drives_handled_status_message_and_retryability", () => {
    // Arrange
    const error = new ApiError(
      { method: "GET", url: "/api/v1/billing/me" } as never,
      {
        body: { detail: "Billing is temporarily unavailable" },
        ok: false,
        status: 503,
        statusText: "Service Unavailable",
        url: "/api/v1/billing/me",
      },
      "Service Unavailable",
    )

    // Act
    const normalized = normalizeAppError(error, "query")

    // Assert
    expect(error).toMatchObject({
      body: { detail: "Billing is temporarily unavailable" },
      request: { method: "GET", url: "/api/v1/billing/me" },
      status: 503,
      statusText: "Service Unavailable",
      url: "/api/v1/billing/me",
    })
    expect(normalized).toMatchObject({
      message: "Billing is temporarily unavailable",
      retryable: true,
      source: "query",
      status: 503,
      title: "Service unavailable",
    })
  })

  test("api_error_without_detail_uses_error_message_fallback_for_unknown_status", () => {
    // Arrange
    const error = new ApiError(
      { method: "POST", url: "/api/v1/brand-intelligence/report" } as never,
      {
        body: {},
        ok: false,
        status: 418,
        statusText: "I'm a teapot",
        url: "/api/v1/brand-intelligence/report",
      },
      "Report generation failed",
    )

    // Act
    const normalized = normalizeAppError(error, "mutation")

    // Assert
    expect(error.status).toBe(418)
    expect(error.body).toEqual({})
    expect(normalized).toMatchObject({
      message: "Report generation failed",
      retryable: true,
      source: "mutation",
      status: 500,
      title: "Something went wrong",
    })
  })

  test("api_error_critical_query_contract_rethrows_403_500_and_503_but_not_401", () => {
    // Arrange
    const forbidden = new ApiError(
      { method: "GET", url: "/api/v1/internal/feature-flags/" } as never,
      {
        body: { detail: "Forbidden" },
        ok: false,
        status: 403,
        statusText: "Forbidden",
        url: "/api/v1/internal/feature-flags/",
      },
      "Forbidden",
    )
    const unauthorized = new ApiError(
      { method: "GET", url: "/api/v1/users/me" } as never,
      {
        body: { detail: "Unauthorized" },
        ok: false,
        status: 401,
        statusText: "Unauthorized",
        url: "/api/v1/users/me",
      },
      "Unauthorized",
    )

    // Act / Assert
    expect(() => rethrowCriticalQueryError(forbidden, "query")).toThrow(
      expect.objectContaining({ status: 403, title: "Access denied" }),
    )
    expect(() => rethrowCriticalQueryError(unauthorized, "query")).not.toThrow()
  })
})
