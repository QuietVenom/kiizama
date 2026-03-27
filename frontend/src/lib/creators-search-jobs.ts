import type { IgScrapeTerminalEventPayload } from "@/features/user-events/types"

export const CREATORS_SEARCH_JOBS_STORAGE_KEY = "kiizama-creators-search-jobs"
export const CREATORS_SEARCH_JOBS_UPDATED_EVENT =
  "kiizama-creators-search-jobs-updated"
export const MAX_CREATORS_SEARCH_JOBS = 10
export const MAX_SCRAPE_JOB_BATCH_SIZE = 10

export type CreatorsSearchJobSourceBox = "expired" | "missing"
export type CreatorsSearchJobStatus = "queued" | "running" | "done" | "failed"

export type CreatorsSearchLocalJob = {
  jobId: string
  sourceBox: CreatorsSearchJobSourceBox
  requestedUsernames: string[]
  batchKey: string
  status: CreatorsSearchJobStatus
  createdAt: string
  updatedAt: string
  readyUsernames: string[]
  error: string | null
  terminalPayload: IgScrapeTerminalEventPayload | null
}

type CreatorsSearchJobsUpdatedDetail = {
  jobs: CreatorsSearchLocalJob[]
}

const isRecord = (value: unknown): value is Record<string, unknown> =>
  typeof value === "object" && value !== null && !Array.isArray(value)

const isStringArray = (value: unknown): value is string[] =>
  Array.isArray(value) && value.every((item) => typeof item === "string")

const isTerminalPayload = (
  value: unknown,
): value is IgScrapeTerminalEventPayload => {
  if (!isRecord(value)) {
    return false
  }

  return (
    value.event_version === 1 &&
    typeof value.notification_id === "string" &&
    typeof value.job_id === "string" &&
    (value.status === "done" || value.status === "failed") &&
    typeof value.created_at === "string" &&
    typeof value.completed_at === "string" &&
    isStringArray(value.requested_usernames) &&
    isStringArray(value.ready_usernames) &&
    isStringArray(value.successful_usernames) &&
    isStringArray(value.skipped_usernames) &&
    isStringArray(value.failed_usernames) &&
    isStringArray(value.not_found_usernames) &&
    isRecord(value.counters) &&
    typeof value.counters.requested === "number" &&
    typeof value.counters.successful === "number" &&
    typeof value.counters.failed === "number" &&
    typeof value.counters.not_found === "number" &&
    (typeof value.error === "string" || value.error === null)
  )
}

const isCreatorsSearchLocalJob = (
  value: unknown,
): value is CreatorsSearchLocalJob => {
  if (!isRecord(value)) {
    return false
  }

  return (
    typeof value.jobId === "string" &&
    (value.sourceBox === "expired" || value.sourceBox === "missing") &&
    isStringArray(value.requestedUsernames) &&
    typeof value.batchKey === "string" &&
    (value.status === "queued" ||
      value.status === "running" ||
      value.status === "done" ||
      value.status === "failed") &&
    typeof value.createdAt === "string" &&
    typeof value.updatedAt === "string" &&
    isStringArray(value.readyUsernames) &&
    (typeof value.error === "string" || value.error === null) &&
    (value.terminalPayload === null || isTerminalPayload(value.terminalPayload))
  )
}

const trimCreatorsSearchJobs = (jobs: CreatorsSearchLocalJob[]) =>
  jobs.slice(0, MAX_CREATORS_SEARCH_JOBS)

const dispatchCreatorsSearchJobsUpdated = (jobs: CreatorsSearchLocalJob[]) => {
  if (typeof window === "undefined") {
    return
  }

  window.dispatchEvent(
    new CustomEvent<CreatorsSearchJobsUpdatedDetail>(
      CREATORS_SEARCH_JOBS_UPDATED_EVENT,
      {
        detail: { jobs },
      },
    ),
  )
}

const persistCreatorsSearchJobs = (jobs: CreatorsSearchLocalJob[]) => {
  const nextJobs = trimCreatorsSearchJobs(jobs)
  if (typeof window === "undefined") {
    return nextJobs
  }

  localStorage.setItem(
    CREATORS_SEARCH_JOBS_STORAGE_KEY,
    JSON.stringify(nextJobs),
  )
  dispatchCreatorsSearchJobsUpdated(nextJobs)
  return nextJobs
}

export const readCreatorsSearchJobs = (): CreatorsSearchLocalJob[] => {
  if (typeof window === "undefined") {
    return []
  }

  try {
    const rawValue = localStorage.getItem(CREATORS_SEARCH_JOBS_STORAGE_KEY)
    if (!rawValue) {
      return []
    }

    const parsedValue: unknown = JSON.parse(rawValue)
    if (!Array.isArray(parsedValue)) {
      return []
    }

    return trimCreatorsSearchJobs(parsedValue.filter(isCreatorsSearchLocalJob))
  } catch {
    return []
  }
}

export const subscribeToCreatorsSearchJobs = (
  callback: (jobs: CreatorsSearchLocalJob[]) => void,
) => {
  if (typeof window === "undefined") {
    return () => undefined
  }

  const handleStorage = (event: StorageEvent) => {
    if (event.key === CREATORS_SEARCH_JOBS_STORAGE_KEY) {
      callback(readCreatorsSearchJobs())
    }
  }

  const handleCustomEvent = (event: Event) => {
    const detail = (event as CustomEvent<CreatorsSearchJobsUpdatedDetail>)
      .detail
    callback(detail?.jobs ?? readCreatorsSearchJobs())
  }

  window.addEventListener("storage", handleStorage)
  window.addEventListener(CREATORS_SEARCH_JOBS_UPDATED_EVENT, handleCustomEvent)

  return () => {
    window.removeEventListener("storage", handleStorage)
    window.removeEventListener(
      CREATORS_SEARCH_JOBS_UPDATED_EVENT,
      handleCustomEvent,
    )
  }
}

export const upsertCreatorsSearchJob = (job: CreatorsSearchLocalJob) => {
  const currentJobs = readCreatorsSearchJobs()
  const nextJobs = currentJobs.filter(
    (currentJob) => currentJob.jobId !== job.jobId,
  )
  nextJobs.unshift(job)
  return persistCreatorsSearchJobs(nextJobs)
}

export const updateCreatorsSearchJob = (
  jobId: string,
  updater: (job: CreatorsSearchLocalJob) => CreatorsSearchLocalJob,
) => {
  const currentJobs = readCreatorsSearchJobs()
  const nextJobs = currentJobs.map((job) =>
    job.jobId === jobId ? updater(job) : job,
  )
  return persistCreatorsSearchJobs(nextJobs)
}

export const removeCreatorsSearchJob = (jobId: string) => {
  const nextJobs = readCreatorsSearchJobs().filter((job) => job.jobId !== jobId)
  return persistCreatorsSearchJobs(nextJobs)
}

export const buildCreatorsSearchBatchKey = (
  sourceBox: CreatorsSearchJobSourceBox,
  usernames: string[],
) => `${sourceBox}:${[...new Set(usernames)].sort().join(",")}`

export const hasActiveCreatorsSearchJob = (batchKey: string) =>
  readCreatorsSearchJobs().some(
    (job) =>
      job.batchKey === batchKey &&
      (job.status === "queued" || job.status === "running"),
  )

export const createBalancedUsernameBatches = (
  usernames: string[],
  maxBatchSize = MAX_SCRAPE_JOB_BATCH_SIZE,
) => {
  if (usernames.length === 0) {
    return []
  }

  const batchCount = Math.ceil(usernames.length / maxBatchSize)
  const minBatchSize = Math.floor(usernames.length / batchCount)
  const remainder = usernames.length % batchCount
  const batches: string[][] = []
  let index = 0

  for (let batchIndex = 0; batchIndex < batchCount; batchIndex += 1) {
    const size = minBatchSize + (batchIndex < remainder ? 1 : 0)
    batches.push(usernames.slice(index, index + size))
    index += size
  }

  return batches
}
