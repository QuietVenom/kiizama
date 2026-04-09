import { OpenAPI } from "@/client"
import { redirectToLoginWithReturnTo } from "@/features/errors/navigation"

import { readUserEventsCursor, writeUserEventsCursor } from "./cursor"
import type { UserEvent } from "./types"
import { normalizeUserEvent } from "./types"

const USER_EVENTS_STREAM_PATH = "/api/v1/events/stream"
const BASE_RECONNECT_DELAY_MS = 1000
const MAX_RECONNECT_DELAY_MS = 30000

type UserEventsConnectionSession = {
  userId: string
}

type ParsedSseEvent = {
  data: string | null
  event: string | null
  id: string | null
  retry: number | null
}

export type UserEventListener = (event: UserEvent) => void

const buildUserEventsUrl = () => `${OpenAPI.BASE}${USER_EVENTS_STREAM_PATH}`

const getAccessToken = () => localStorage.getItem("access_token") || ""

const parseEventData = (data: string | null): unknown => {
  if (data === null) {
    return null
  }

  try {
    return JSON.parse(data)
  } catch {
    return null
  }
}

const splitLine = (line: string) => {
  const separatorIndex = line.indexOf(":")
  if (separatorIndex === -1) {
    return {
      field: line,
      value: "",
    }
  }

  const rawValue = line.slice(separatorIndex + 1)
  return {
    field: line.slice(0, separatorIndex),
    value: rawValue.startsWith(" ") ? rawValue.slice(1) : rawValue,
  }
}

async function* parseSseStream(
  stream: ReadableStream<Uint8Array>,
): AsyncGenerator<ParsedSseEvent> {
  const reader = stream.getReader()
  const decoder = new TextDecoder()
  let buffer = ""
  let currentEvent: ParsedSseEvent = {
    data: null,
    event: null,
    id: null,
    retry: null,
  }

  const flushEvent = () => {
    if (
      currentEvent.data === null &&
      currentEvent.event === null &&
      currentEvent.id === null &&
      currentEvent.retry === null
    ) {
      return null
    }

    const completedEvent = currentEvent
    currentEvent = {
      data: null,
      event: null,
      id: null,
      retry: null,
    }
    return completedEvent
  }

  try {
    while (true) {
      const { done, value } = await reader.read()
      if (done) {
        break
      }

      buffer += decoder.decode(value, { stream: true })

      while (true) {
        const lineBreakIndex = buffer.indexOf("\n")
        if (lineBreakIndex === -1) {
          break
        }

        const rawLine = buffer.slice(0, lineBreakIndex)
        buffer = buffer.slice(lineBreakIndex + 1)
        const line = rawLine.endsWith("\r") ? rawLine.slice(0, -1) : rawLine

        if (line === "") {
          const completedEvent = flushEvent()
          if (completedEvent) {
            yield completedEvent
          }
          continue
        }

        if (line.startsWith(":")) {
          continue
        }

        const { field, value: fieldValue } = splitLine(line)
        if (field === "data") {
          currentEvent.data =
            currentEvent.data === null
              ? fieldValue
              : `${currentEvent.data}\n${fieldValue}`
        } else if (field === "event") {
          currentEvent.event = fieldValue
        } else if (field === "id") {
          currentEvent.id = fieldValue
        } else if (field === "retry") {
          const retryValue = Number.parseInt(fieldValue, 10)
          if (Number.isFinite(retryValue) && retryValue >= 0) {
            currentEvent.retry = retryValue
          }
        }
      }
    }

    buffer += decoder.decode()
    if (buffer.length > 0) {
      const line = buffer.endsWith("\r") ? buffer.slice(0, -1) : buffer
      if (!line.startsWith(":")) {
        const { field, value } = splitLine(line)
        if (field === "data") {
          currentEvent.data =
            currentEvent.data === null
              ? value
              : `${currentEvent.data}\n${value}`
        } else if (field === "event") {
          currentEvent.event = value
        } else if (field === "id") {
          currentEvent.id = value
        } else if (field === "retry") {
          const retryValue = Number.parseInt(value, 10)
          if (Number.isFinite(retryValue) && retryValue >= 0) {
            currentEvent.retry = retryValue
          }
        }
      }
    }

    const completedEvent = flushEvent()
    if (completedEvent) {
      yield completedEvent
    }
  } finally {
    reader.releaseLock()
  }
}

class UserEventsConnection {
  private abortController: AbortController | null = null
  private listeners = new Set<UserEventListener>()
  private reconnectAttempts = 0
  private reconnectDelayOverrideMs: number | null = null
  private reconnectTimer: number | null = null
  private retainCount = 0
  private runId = 0
  private session: UserEventsConnectionSession | null = null

  retain(session: UserEventsConnectionSession) {
    this.retainCount += 1
    const shouldRestart = this.session?.userId !== session.userId
    this.session = session

    if (shouldRestart) {
      this.restart()
    } else {
      this.ensureConnected()
    }

    return () => {
      this.retainCount = Math.max(0, this.retainCount - 1)
      if (this.retainCount === 0) {
        this.shutdown()
      }
    }
  }

  subscribe(listener: UserEventListener) {
    this.listeners.add(listener)

    return () => {
      this.listeners.delete(listener)
    }
  }

  private emit(event: UserEvent) {
    for (const listener of this.listeners) {
      listener(event)
    }
  }

  private ensureConnected() {
    if (this.session === null) {
      return
    }

    if (this.abortController !== null || this.reconnectTimer !== null) {
      return
    }

    void this.connect(this.runId, this.session)
  }

  private restart() {
    this.runId += 1
    this.reconnectAttempts = 0
    this.reconnectDelayOverrideMs = null
    this.clearReconnectTimer()
    this.abortController?.abort()
    this.abortController = null
    this.ensureConnected()
  }

  private shutdown() {
    this.runId += 1
    this.session = null
    this.reconnectAttempts = 0
    this.reconnectDelayOverrideMs = null
    this.clearReconnectTimer()
    this.abortController?.abort()
    this.abortController = null
  }

  private clearReconnectTimer() {
    if (this.reconnectTimer !== null) {
      window.clearTimeout(this.reconnectTimer)
      this.reconnectTimer = null
    }
  }

  private scheduleReconnect(runId: number, userId: string) {
    if (
      this.session === null ||
      this.session.userId !== userId ||
      this.runId !== runId ||
      this.reconnectTimer !== null
    ) {
      return
    }

    const delay =
      this.reconnectDelayOverrideMs ??
      Math.min(
        BASE_RECONNECT_DELAY_MS * 2 ** this.reconnectAttempts,
        MAX_RECONNECT_DELAY_MS,
      )
    this.reconnectAttempts += 1

    this.reconnectTimer = window.setTimeout(() => {
      this.reconnectTimer = null
      this.ensureConnected()
    }, delay)
  }

  private async connect(runId: number, session: UserEventsConnectionSession) {
    const token = getAccessToken()
    if (!token) {
      return
    }

    const controller = new AbortController()
    this.abortController = controller
    let shouldReconnect = false

    try {
      const headers = new Headers({
        Accept: "text/event-stream",
        Authorization: `Bearer ${token}`,
        "Cache-Control": "no-cache",
      })
      const lastEventId = readUserEventsCursor(session.userId)
      if (lastEventId) {
        headers.set("Last-Event-ID", lastEventId)
      }

      // Use fetch because the generated client does not expose the SSE body stream.
      const response = await fetch(buildUserEventsUrl(), {
        headers,
        method: "GET",
        signal: controller.signal,
      })

      if (controller.signal.aborted || this.runId !== runId) {
        return
      }

      if (response.status === 401) {
        this.shutdown()
        redirectToLoginWithReturnTo()
        return
      }

      if (response.status === 403) {
        this.shutdown()
        return
      }

      if (!response.ok || response.body === null) {
        shouldReconnect = true
        return
      }

      this.reconnectAttempts = 0

      for await (const serverEvent of parseSseStream(response.body)) {
        if (controller.signal.aborted || this.runId !== runId) {
          return
        }

        if (serverEvent.retry !== null) {
          this.reconnectDelayOverrideMs = serverEvent.retry
        }

        const normalizedEvent = normalizeUserEvent({
          data: parseEventData(serverEvent.data),
          event: serverEvent.event,
          id: serverEvent.id,
        })
        if (!normalizedEvent) {
          continue
        }

        writeUserEventsCursor(session.userId, normalizedEvent.id)
        this.emit(normalizedEvent)
      }

      shouldReconnect = true
    } catch {
      if (!controller.signal.aborted) {
        shouldReconnect = true
      }
    } finally {
      if (this.abortController === controller) {
        this.abortController = null
      }

      if (shouldReconnect) {
        this.scheduleReconnect(runId, session.userId)
      }
    }
  }
}

const userEventsConnection = new UserEventsConnection()

export const retainUserEventsConnection = (
  session: UserEventsConnectionSession,
) => userEventsConnection.retain(session)

export const subscribeToUserEvents = (listener: UserEventListener) =>
  userEventsConnection.subscribe(listener)
