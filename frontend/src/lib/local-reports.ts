import { formatDate } from "@/i18n"
import { blobToDataUrl, triggerFileDownload } from "@/lib/report-files"

export const LOCAL_REPORTS_STORAGE_KEY = "kiizama-overview-local-reports"
export const LOCAL_REPORTS_UPDATED_EVENT = "kiizama-local-reports-updated"
export const MAX_LOCAL_REPORTS = 5

export type LocalReportItem = {
  id: string
  name: string
  createdAt: string
  dataUrl: string
  mimeType: string
  sizeBytes: number
  reportType: string
  source: string
}

type SaveLocalReportParams = {
  blob: Blob
  filename: string
  reportType: string
  source: string
}

type LocalReportsUpdatedDetail = {
  reports: LocalReportItem[]
}

const isLocalReportItem = (value: unknown): value is LocalReportItem => {
  if (!value || typeof value !== "object") return false

  const report = value as Record<string, unknown>

  return (
    typeof report.id === "string" &&
    typeof report.name === "string" &&
    typeof report.createdAt === "string" &&
    typeof report.dataUrl === "string" &&
    typeof report.mimeType === "string" &&
    typeof report.sizeBytes === "number" &&
    typeof report.reportType === "string" &&
    typeof report.source === "string"
  )
}

const buildReportId = () => {
  if (
    typeof crypto !== "undefined" &&
    typeof crypto.randomUUID === "function"
  ) {
    return crypto.randomUUID()
  }

  return `report-${Date.now()}-${Math.random().toString(16).slice(2)}`
}

const trimLocalReports = (reports: LocalReportItem[]) =>
  reports.slice(0, MAX_LOCAL_REPORTS)

const dispatchLocalReportsUpdated = (reports: LocalReportItem[]) => {
  if (typeof window === "undefined") return

  window.dispatchEvent(
    new CustomEvent<LocalReportsUpdatedDetail>(LOCAL_REPORTS_UPDATED_EVENT, {
      detail: { reports },
    }),
  )
}

const persistLocalReports = (reports: LocalReportItem[]) => {
  if (typeof window === "undefined") {
    return trimLocalReports(reports)
  }

  let nextReports = trimLocalReports(reports)

  while (nextReports.length > 0) {
    try {
      localStorage.setItem(
        LOCAL_REPORTS_STORAGE_KEY,
        JSON.stringify(nextReports),
      )
      dispatchLocalReportsUpdated(nextReports)
      return nextReports
    } catch (error) {
      const isQuotaError =
        error instanceof DOMException &&
        (error.name === "QuotaExceededError" ||
          error.name === "NS_ERROR_DOM_QUOTA_REACHED")

      if (!isQuotaError) {
        throw error
      }

      if (nextReports.length === 1) {
        throw error
      }

      nextReports = nextReports.slice(0, -1)
    }
  }

  localStorage.removeItem(LOCAL_REPORTS_STORAGE_KEY)
  dispatchLocalReportsUpdated([])
  return []
}

export const readLocalReports = (): LocalReportItem[] => {
  if (typeof window === "undefined") return []

  try {
    const rawValue = localStorage.getItem(LOCAL_REPORTS_STORAGE_KEY)
    if (!rawValue) return []

    const parsedValue: unknown = JSON.parse(rawValue)
    if (!Array.isArray(parsedValue)) return []

    return trimLocalReports(parsedValue.filter(isLocalReportItem))
  } catch {
    return []
  }
}

export const subscribeToLocalReports = (
  callback: (reports: LocalReportItem[]) => void,
) => {
  if (typeof window === "undefined") {
    return () => undefined
  }

  const handleStorage = (event: StorageEvent) => {
    if (event.key === LOCAL_REPORTS_STORAGE_KEY) {
      callback(readLocalReports())
    }
  }

  const handleCustomEvent = (event: Event) => {
    const detail = (event as CustomEvent<LocalReportsUpdatedDetail>).detail
    callback(detail?.reports ?? readLocalReports())
  }

  window.addEventListener("storage", handleStorage)
  window.addEventListener(LOCAL_REPORTS_UPDATED_EVENT, handleCustomEvent)

  return () => {
    window.removeEventListener("storage", handleStorage)
    window.removeEventListener(LOCAL_REPORTS_UPDATED_EVENT, handleCustomEvent)
  }
}

export const saveLocalReport = async ({
  blob,
  filename,
  reportType,
  source,
}: SaveLocalReportParams) => {
  const dataUrl = await blobToDataUrl(blob)
  const nextItem: LocalReportItem = {
    id: buildReportId(),
    name: filename,
    createdAt: new Date().toISOString(),
    dataUrl,
    mimeType: blob.type || "application/octet-stream",
    sizeBytes: blob.size,
    reportType,
    source,
  }

  persistLocalReports([nextItem, ...readLocalReports()])
  return nextItem
}

export const deleteLocalReport = (reportId: string) => {
  const nextReports = readLocalReports().filter(
    (report) => report.id !== reportId,
  )
  persistLocalReports(nextReports)
  return nextReports
}

export const clearLocalReports = () => {
  if (typeof window === "undefined") return

  localStorage.removeItem(LOCAL_REPORTS_STORAGE_KEY)
  dispatchLocalReportsUpdated([])
}

export const downloadLocalReport = (report: LocalReportItem) => {
  triggerFileDownload(report.dataUrl, report.name)
}

export const formatLocalReportDate = (
  createdAt: string,
  language?: string | null,
) => {
  const parsedDate = new Date(createdAt)
  if (Number.isNaN(parsedDate.getTime())) {
    return createdAt
  }

  return formatDate(parsedDate, language, {
    day: "2-digit",
    month: "short",
    year: "numeric",
  })
}
