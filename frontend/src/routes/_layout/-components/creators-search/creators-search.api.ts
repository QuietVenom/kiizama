import { OpenAPI } from "@/client"
import { createIdempotencyKey } from "@/features/billing/api"
import {
  buildCreatorsSearchBatchKey,
  type CreatorsSearchJobSourceBox,
  type CreatorsSearchJobStatus,
  createBalancedUsernameBatches,
  hasActiveCreatorsSearchJob,
  upsertCreatorsSearchJob,
} from "@/lib/creators-search-jobs"
import {
  downloadBlob,
  extractFilenameFromContentDisposition,
} from "@/lib/report-files"

const REPORT_ENDPOINT_PATH = "/api/v1/social-media-report/instagram"

const handleUnauthorizedResponse = () => {
  localStorage.removeItem("access_token")
  window.location.href = "/login"
}

export const generateInstagramReportPdf = async (username: string) => {
  const token = localStorage.getItem("access_token") || ""
  const response = await fetch(`${OpenAPI.BASE}${REPORT_ENDPOINT_PATH}`, {
    method: "POST",
    headers: {
      Authorization: `Bearer ${token}`,
      "Content-Type": "application/json",
      Accept: "application/pdf",
      "Idempotency-Key": createIdempotencyKey(),
    },
    body: JSON.stringify({
      usernames: [username],
      generate_html: false,
      generate_pdf: true,
    }),
  })

  if (response.status === 401) {
    handleUnauthorizedResponse()
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
    `${username}_report.pdf`,
  )

  downloadBlob(blob, filename)
}

export const enqueueCreatorsSearchScrapeJobs = async (
  sourceBox: CreatorsSearchJobSourceBox,
  requestedUsernames: string[],
) => {
  const batches = createBalancedUsernameBatches(requestedUsernames)
  let createdCount = 0
  let skippedCount = 0

  for (const batch of batches) {
    const batchKey = buildCreatorsSearchBatchKey(sourceBox, batch)
    if (hasActiveCreatorsSearchJob(batchKey)) {
      skippedCount += 1
      continue
    }

    const token = localStorage.getItem("access_token") || ""
    const rawResponse = await fetch(
      `${OpenAPI.BASE}/api/v1/ig-scraper/jobs/apify`,
      {
        method: "POST",
        headers: {
          Authorization: `Bearer ${token}`,
          "Content-Type": "application/json",
          Accept: "application/json",
          "Idempotency-Key": createIdempotencyKey(),
        },
        body: JSON.stringify({
          usernames: batch,
        }),
      },
    )
    if (rawResponse.status === 401) {
      handleUnauthorizedResponse()
      throw new Error("Your session has expired. Please log in again.")
    }
    if (!rawResponse.ok) {
      const errorBody = (await rawResponse.json().catch(() => ({}))) as {
        detail?: string
      }
      throw new Error(errorBody.detail || "Unable to create scrape job.")
    }
    const response = (await rawResponse.json()) as {
      job_id: string
      status: CreatorsSearchJobStatus
    }
    const now = new Date().toISOString()

    upsertCreatorsSearchJob({
      jobId: response.job_id,
      sourceBox,
      requestedUsernames: batch,
      batchKey,
      status: response.status,
      createdAt: now,
      updatedAt: now,
      readyUsernames: [],
      error: null,
      terminalPayload: null,
    })
    createdCount += 1
  }

  return {
    batchCount: batches.length,
    createdCount,
    skippedCount,
  }
}
