type JsonObject = Record<string, unknown>

const isRecord = (value: unknown): value is JsonObject =>
  typeof value === "object" && value !== null && !Array.isArray(value)

const isStringArray = (value: unknown): value is string[] =>
  Array.isArray(value) && value.every((item) => typeof item === "string")

export type KnownUserEventName =
  | "ig-scrape.job.completed"
  | "ig-scrape.job.failed"

export type UserEventName = KnownUserEventName | (string & {})

export interface UserEventEnvelope<TPayload = JsonObject> {
  topic: string
  source: string
  kind: string
  notification_id: string
  payload: TPayload
}

export interface IgScrapeTerminalEventCounters {
  requested: number
  successful: number
  failed: number
  not_found: number
}

export interface IgScrapeTerminalEventPayload {
  event_version: 1
  notification_id: string
  job_id: string
  status: "done" | "failed"
  created_at: string
  completed_at: string
  requested_usernames: string[]
  ready_usernames: string[]
  successful_usernames: string[]
  skipped_usernames: string[]
  failed_usernames: string[]
  not_found_usernames: string[]
  counters: IgScrapeTerminalEventCounters
  error: string | null
}

export type IgScrapeJobCompletedEvent = {
  id: string
  name: "ig-scrape.job.completed"
  envelope: UserEventEnvelope<IgScrapeTerminalEventPayload>
}

export type IgScrapeJobFailedEvent = {
  id: string
  name: "ig-scrape.job.failed"
  envelope: UserEventEnvelope<IgScrapeTerminalEventPayload>
}

export type UserEvent =
  | IgScrapeJobCompletedEvent
  | IgScrapeJobFailedEvent
  | {
      id: string
      name: UserEventName
      envelope: UserEventEnvelope
    }

type UserEventCandidate = {
  data: unknown
  event: string | null
  id: string | null
}

const isNonEmptyString = (value: unknown): value is string =>
  typeof value === "string" && value.length > 0

const isTerminalCounters = (
  value: unknown,
): value is IgScrapeTerminalEventCounters => {
  if (!isRecord(value)) {
    return false
  }

  return (
    typeof value.requested === "number" &&
    typeof value.successful === "number" &&
    typeof value.failed === "number" &&
    typeof value.not_found === "number"
  )
}

const isTerminalPayload = (
  value: unknown,
): value is IgScrapeTerminalEventPayload => {
  if (!isRecord(value)) {
    return false
  }

  return (
    value.event_version === 1 &&
    isNonEmptyString(value.notification_id) &&
    isNonEmptyString(value.job_id) &&
    (value.status === "done" || value.status === "failed") &&
    isNonEmptyString(value.created_at) &&
    isNonEmptyString(value.completed_at) &&
    isStringArray(value.requested_usernames) &&
    isStringArray(value.ready_usernames) &&
    isStringArray(value.successful_usernames) &&
    isStringArray(value.skipped_usernames) &&
    isStringArray(value.failed_usernames) &&
    isStringArray(value.not_found_usernames) &&
    isTerminalCounters(value.counters) &&
    (typeof value.error === "string" || value.error === null)
  )
}

const isUserEventEnvelope = (value: unknown): value is UserEventEnvelope => {
  if (!isRecord(value)) {
    return false
  }

  return (
    isNonEmptyString(value.topic) &&
    isNonEmptyString(value.source) &&
    isNonEmptyString(value.kind) &&
    isNonEmptyString(value.notification_id) &&
    isRecord(value.payload)
  )
}

export const normalizeUserEvent = (
  candidate: UserEventCandidate,
): UserEvent | null => {
  if (!isNonEmptyString(candidate.id) || !isNonEmptyString(candidate.event)) {
    return null
  }

  if (!isUserEventEnvelope(candidate.data)) {
    return null
  }

  if (
    candidate.event === "ig-scrape.job.completed" ||
    candidate.event === "ig-scrape.job.failed"
  ) {
    if (!isTerminalPayload(candidate.data.payload)) {
      return null
    }

    const expectedStatus =
      candidate.event === "ig-scrape.job.completed" ? "done" : "failed"

    if (candidate.data.payload.status !== expectedStatus) {
      return null
    }

    return {
      id: candidate.id,
      name: candidate.event,
      envelope: candidate.data,
    }
  }

  return {
    id: candidate.id,
    name: candidate.event,
    envelope: candidate.data,
  }
}

export const isIgScrapeJobCompletedEvent = (
  event: UserEvent,
): event is IgScrapeJobCompletedEvent =>
  event.name === "ig-scrape.job.completed"

export const isIgScrapeJobFailedEvent = (
  event: UserEvent,
): event is IgScrapeJobFailedEvent => event.name === "ig-scrape.job.failed"
