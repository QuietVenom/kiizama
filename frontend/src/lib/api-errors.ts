import { ApiError } from "@/client"

export const extractApiErrorMessage = (
  error: unknown,
  fallbackMessage = "Unable to complete the request.",
) => {
  if (error instanceof ApiError) {
    const detail = (error.body as { detail?: Array<{ msg?: string }> | string })
      ?.detail

    if (Array.isArray(detail) && detail.length > 0) {
      return detail[0]?.msg || fallbackMessage
    }

    if (typeof detail === "string") {
      return detail
    }

    return error.message || fallbackMessage
  }

  if (error instanceof Error) {
    return error.message
  }

  return fallbackMessage
}
