import {
  BrandIntelligenceService,
  OpenAPI,
  type ReputationCampaignStrategyRequest,
  type ReputationCreatorStrategyRequest,
} from "@/client"
import { extractFilenameFromContentDisposition } from "@/lib/report-files"

export const BRAND_INTELLIGENCE_CAMPAIGN_ENDPOINT =
  "/api/v1/brand-intelligence/reputation-campaign-strategy"
export const BRAND_INTELLIGENCE_CREATOR_ENDPOINT =
  "/api/v1/brand-intelligence/reputation-creator-strategy"

type BrandIntelligenceReportRequest =
  | ReputationCampaignStrategyRequest
  | ReputationCreatorStrategyRequest

type GenerateBrandIntelligenceReportParams = {
  endpointPath:
    | typeof BRAND_INTELLIGENCE_CAMPAIGN_ENDPOINT
    | typeof BRAND_INTELLIGENCE_CREATOR_ENDPOINT
  fallbackFilename: string
  payload: BrandIntelligenceReportRequest
}

const safeSlug = (value: string | null | undefined) => {
  if (!value) {
    return ""
  }

  return value
    .replace(/[^a-zA-Z0-9_-]+/g, "_")
    .replace(/^_+|_+$/g, "")
    .toLowerCase()
}

const buildBrandIntelligenceFallbackFilename = ({
  endpointPath,
  fallbackFilename,
  payload,
}: GenerateBrandIntelligenceReportParams) => {
  const extension = fallbackFilename.split(".").pop()

  if (!extension) {
    return fallbackFilename
  }

  if (
    endpointPath === BRAND_INTELLIGENCE_CAMPAIGN_ENDPOINT &&
    "brand_name" in payload
  ) {
    const slug = safeSlug(payload.brand_name)

    if (slug) {
      return `reputation_campaign_strategy_${slug}.${extension}`
    }
  }

  if (
    endpointPath === BRAND_INTELLIGENCE_CREATOR_ENDPOINT &&
    "creator_username" in payload
  ) {
    const slug = safeSlug(payload.creator_username)

    if (slug) {
      return `reputation_creator_strategy_${slug}.${extension}`
    }
  }

  return fallbackFilename
}

export const readProfilesExistence = (usernames: string[]) =>
  BrandIntelligenceService.readProfilesExistence({ usernames })

export const generateBrandIntelligenceReport = async ({
  endpointPath,
  fallbackFilename,
  payload,
}: GenerateBrandIntelligenceReportParams) => {
  const resolvedFallbackFilename = buildBrandIntelligenceFallbackFilename({
    endpointPath,
    fallbackFilename,
    payload,
  })
  const token = localStorage.getItem("access_token") || ""
  const response = await fetch(`${OpenAPI.BASE}${endpointPath}`, {
    method: "POST",
    headers: {
      Authorization: `Bearer ${token}`,
      "Content-Type": "application/json",
      Accept: "application/pdf, application/zip",
    },
    body: JSON.stringify(payload),
  })

  if ([401, 403].includes(response.status)) {
    localStorage.removeItem("access_token")
    window.location.href = "/login"
    throw new Error("Your session has expired. Please log in again.")
  }

  if (!response.ok) {
    try {
      const errorBody = (await response.json()) as {
        detail?: Array<{ msg?: string }> | string
      }

      if (Array.isArray(errorBody.detail) && errorBody.detail[0]?.msg) {
        throw new Error(errorBody.detail[0].msg)
      }

      if (typeof errorBody.detail === "string") {
        throw new Error(errorBody.detail)
      }
    } catch (error) {
      if (error instanceof Error) {
        throw error
      }
    }

    throw new Error("Unable to generate the report.")
  }

  const blob = await response.blob()
  const filename = extractFilenameFromContentDisposition(
    response.headers.get("Content-Disposition"),
    resolvedFallbackFilename,
  )

  return {
    blob,
    contentType: response.headers.get("Content-Type") || blob.type,
    filename,
  }
}
