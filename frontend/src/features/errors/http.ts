import { isNotFound } from "@tanstack/react-router"
import { ApiError } from "@/client"

export type HandledStatusCode = 401 | 403 | 404 | 500 | 503

export type AppErrorSource =
  | "router"
  | "loader"
  | "query"
  | "mutation"
  | "unknown"

export type AppHttpError = {
  message: string
  retryable: boolean
  source: AppErrorSource
  status: HandledStatusCode
  title: string
}

const getApiErrorMessage = (
  error: ApiError,
  fallbackMessage: string,
): string => {
  const detail = (error.body as { detail?: Array<{ msg?: string }> | string })
    ?.detail

  if (Array.isArray(detail) && detail.length > 0) {
    return detail[0]?.msg || fallbackMessage
  }

  if (typeof detail === "string" && detail.trim().length > 0) {
    return detail
  }

  return error.message || fallbackMessage
}

const buildAppHttpError = (
  status: HandledStatusCode,
  source: AppErrorSource,
  message?: string,
): AppHttpError => {
  switch (status) {
    case 401:
      return {
        status,
        source,
        retryable: false,
        title: "Unauthorized",
        message: message || "Your session is no longer valid.",
      }
    case 403:
      return {
        status,
        source,
        retryable: false,
        title: "Access denied",
        message:
          message ||
          "You do not have permission to access this resource or page.",
      }
    case 404:
      return {
        status,
        source,
        retryable: false,
        title: "Page not found",
        message: message || "The page you are looking for was not found.",
      }
    case 500:
      return {
        status,
        source,
        retryable: true,
        title: "Something went wrong",
        message:
          message ||
          "An unexpected error prevented this page from loading correctly.",
      }
    case 503:
      return {
        status,
        source,
        retryable: true,
        title: "Service unavailable",
        message:
          message ||
          "This service is temporarily unavailable. Please try again in a moment.",
      }
  }
}

export const isHandledStatus = (status: number): status is HandledStatusCode =>
  status === 401 ||
  status === 403 ||
  status === 404 ||
  status === 500 ||
  status === 503

export const isRetryableStatus = (status: HandledStatusCode) =>
  status === 500 || status === 503

export const isAppHttpError = (error: unknown): error is AppHttpError => {
  if (typeof error !== "object" || error === null) {
    return false
  }

  const candidate = error as Partial<AppHttpError>

  return (
    typeof candidate.status === "number" &&
    isHandledStatus(candidate.status) &&
    typeof candidate.title === "string" &&
    typeof candidate.message === "string" &&
    typeof candidate.retryable === "boolean" &&
    typeof candidate.source === "string"
  )
}

export const normalizeAppError = (
  error: unknown,
  source: AppErrorSource = "unknown",
): AppHttpError => {
  if (error instanceof ApiError) {
    if (isHandledStatus(error.status)) {
      return buildAppHttpError(
        error.status,
        source,
        getApiErrorMessage(error, error.message),
      )
    }

    return buildAppHttpError(
      500,
      source,
      getApiErrorMessage(error, "Unable to complete the request."),
    )
  }

  if (isAppHttpError(error)) {
    return error
  }

  if (isNotFound(error)) {
    return buildAppHttpError(404, source)
  }

  if (error instanceof Error) {
    return buildAppHttpError(500, source, error.message)
  }

  return buildAppHttpError(500, source)
}

export const rethrowCriticalQueryError = (
  error: unknown,
  source: AppErrorSource = "query",
) => {
  if (!error) {
    return
  }

  const normalizedError = normalizeAppError(error, source)

  if (
    normalizedError.status === 403 ||
    normalizedError.status === 500 ||
    normalizedError.status === 503
  ) {
    throw normalizedError
  }
}
