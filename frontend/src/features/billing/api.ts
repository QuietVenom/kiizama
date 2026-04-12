import type { QueryClient } from "@tanstack/react-query"
import { OpenAPI } from "@/client"

export type BillingFeatureUsage = {
  code: string
  name: string
  limit: number | null
  used: number
  reserved: number
  remaining: number | null
  is_unlimited: boolean
}

export type BillingNotice = {
  id: string
  notice_type:
    | "invoice_upcoming"
    | "trial_will_end"
    | "subscription_paused"
    | "access_revoked"
  status: "unread" | "read" | "dismissed"
  title: string
  message: string
  effective_at: string | null
  expires_at: string | null
  created_at: string
}

export type BillingSummary = {
  access_profile: "standard" | "ambassador"
  managed_access_source: "admin" | "ambassador" | null
  billing_eligible: boolean
  trial_eligible: boolean
  plan_status: "trial" | "base" | "ambassador" | "none"
  subscription_status: string | null
  latest_invoice_status: string | null
  access_revoked_reason: string | null
  pending_ambassador_activation: boolean
  cancel_at: string | null
  current_period_start: string | null
  current_period_end: string | null
  renewal_day: string | null
  features: BillingFeatureUsage[]
  notices: BillingNotice[]
}

type BillingSessionResponse = {
  url: string
}

type BillingNoticeCollectionResponse = {
  data: BillingNotice[]
}

export const billingSummaryQueryKey = ["billing", "me"] as const
export const billingNoticesQueryKey = ["billing", "notices"] as const
const BILLING_QUERY_STALE_TIME_MS = 30_000

const getAccessToken = () => localStorage.getItem("access_token") || ""

const parseErrorResponse = async (response: Response) => {
  try {
    const body = (await response.json()) as { detail?: string }
    if (typeof body.detail === "string" && body.detail) {
      return body.detail
    }
  } catch {
    // Ignore JSON parsing issues and fall through to generic messages.
  }

  return "Unable to complete the billing request."
}

const billingFetch = async <T>(
  path: string,
  init?: RequestInit,
): Promise<T> => {
  const response = await fetch(`${OpenAPI.BASE}${path}`, {
    ...init,
    headers: {
      Authorization: `Bearer ${getAccessToken()}`,
      ...(init?.headers ?? {}),
    },
  })

  if (response.status === 401) {
    localStorage.removeItem("access_token")
    window.location.href = "/login"
    throw new Error("Your session has expired. Please log in again.")
  }

  if (!response.ok) {
    throw new Error(await parseErrorResponse(response))
  }

  return (await response.json()) as T
}

export const readBillingMe = () =>
  billingFetch<BillingSummary>("/api/v1/billing/me", {
    method: "GET",
  })

export const billingSummaryQueryOptions = {
  queryKey: billingSummaryQueryKey,
  queryFn: readBillingMe,
  staleTime: BILLING_QUERY_STALE_TIME_MS,
} as const

export const createCheckoutSession = () =>
  billingFetch<BillingSessionResponse>("/api/v1/billing/checkout-session", {
    method: "POST",
  })

export const createPortalSession = () =>
  billingFetch<BillingSessionResponse>("/api/v1/billing/portal-session", {
    method: "POST",
  })

export const readBillingNotices = () =>
  billingFetch<BillingNoticeCollectionResponse>("/api/v1/billing/notices", {
    method: "GET",
  })

export const billingNoticesQueryOptions = {
  queryKey: billingNoticesQueryKey,
  queryFn: readBillingNotices,
  staleTime: BILLING_QUERY_STALE_TIME_MS,
} as const

export const markBillingNoticeRead = (noticeId: string) =>
  billingFetch<BillingNotice>(`/api/v1/billing/notices/${noticeId}/read`, {
    method: "POST",
  })

export const dismissBillingNotice = (noticeId: string) =>
  billingFetch<BillingNotice>(`/api/v1/billing/notices/${noticeId}/dismiss`, {
    method: "POST",
  })

export const invalidateBillingSummary = (queryClient: QueryClient) =>
  queryClient.invalidateQueries({ queryKey: billingSummaryQueryKey })

export const getFeatureUsage = (
  summary: BillingSummary | undefined,
  code: string,
) => {
  const aliases: Record<string, string[]> = {
    ig_scraper: ["ig_scraper_apify"],
  }

  return summary?.features.find(
    (feature) =>
      feature.code === code || (aliases[code] ?? []).includes(feature.code),
  )
}

export const createIdempotencyKey = () => {
  if (
    typeof crypto !== "undefined" &&
    typeof crypto.randomUUID === "function"
  ) {
    return crypto.randomUUID()
  }
  return `${Date.now()}-${Math.random().toString(16).slice(2)}`
}
