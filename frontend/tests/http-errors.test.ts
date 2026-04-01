import assert from "node:assert/strict"
import test from "node:test"
import { ApiError } from "../src/client/core/ApiError.ts"
import {
  isHandledStatus,
  isRetryableStatus,
  normalizeAppError,
  rethrowCriticalQueryError,
} from "../src/features/errors/http.ts"
import {
  buildLoginHrefWithReturnTo,
  sanitizeReturnTo,
} from "../src/features/errors/navigation.ts"

const createApiError = (status: number, detail?: string) =>
  new ApiError(
    {
      method: "GET",
      url: "/api/test",
    } as never,
    {
      body: detail ? { detail } : undefined,
      ok: false,
      status,
      statusText: "Error",
      url: "/api/test",
    },
    detail || "Error",
  )

test("normalizes handled API status codes", () => {
  assert.equal(normalizeAppError(createApiError(403), "loader").status, 403)
  assert.equal(normalizeAppError(createApiError(503), "query").status, 503)
  assert.equal(normalizeAppError(createApiError(401), "mutation").status, 401)
})

test("maps unknown errors to 500 and keeps retryability only for 500/503", () => {
  const normalizedUnknownError = normalizeAppError(
    new Error("Unexpected failure"),
    "unknown",
  )

  assert.equal(normalizedUnknownError.status, 500)
  assert.equal(isRetryableStatus(500), true)
  assert.equal(isRetryableStatus(503), true)
  assert.equal(isRetryableStatus(403), false)
  assert.equal(isHandledStatus(404), true)
  assert.equal(isHandledStatus(418), false)
})

test("builds safe login redirect URLs", () => {
  assert.equal(
    buildLoginHrefWithReturnTo("/overview?tab=reports"),
    "/login?redirect=%2Foverview%3Ftab%3Dreports",
  )
  assert.equal(buildLoginHrefWithReturnTo("https://evil.example"), "/login")
  assert.equal(sanitizeReturnTo("/brand-intelligence"), "/brand-intelligence")
  assert.equal(sanitizeReturnTo("//evil.example"), undefined)
})

test("rethrows handled critical query errors for 403, 500 and 503", () => {
  assert.throws(
    () => rethrowCriticalQueryError(createApiError(403), "query"),
    (error: unknown) =>
      typeof error === "object" &&
      error !== null &&
      (error as { status?: unknown }).status === 403,
  )
  assert.throws(
    () => rethrowCriticalQueryError(createApiError(500), "query"),
    (error: unknown) =>
      typeof error === "object" &&
      error !== null &&
      (error as { status?: unknown }).status === 500,
  )
  assert.throws(
    () => rethrowCriticalQueryError(createApiError(503), "query"),
    (error: unknown) =>
      typeof error === "object" &&
      error !== null &&
      (error as { status?: unknown }).status === 503,
  )
})

test("does not rethrow 401 or empty query errors", () => {
  assert.doesNotThrow(() => rethrowCriticalQueryError(undefined, "query"))
  assert.doesNotThrow(() =>
    rethrowCriticalQueryError(createApiError(401), "query"),
  )
})
