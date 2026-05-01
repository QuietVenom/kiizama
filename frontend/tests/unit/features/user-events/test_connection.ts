import { beforeEach, describe, expect, test, vi } from "vitest"

const { navigation } = vi.hoisted(() => ({
  navigation: {
    redirectToLoginWithReturnTo: vi.fn(),
  },
}))

vi.mock("@/features/errors/navigation", () => ({
  redirectToLoginWithReturnTo: navigation.redirectToLoginWithReturnTo,
}))

const { OpenAPI } = await import("../../../../src/client")
const { UserEventsConnection, parseSseText } = await import(
  "../../../../src/features/user-events/connection"
)
const { readUserEventsCursor, writeUserEventsCursor } = await import(
  "../../../../src/features/user-events/cursor"
)

const createSseStream = (text: string) => {
  const encoder = new TextEncoder()

  return new ReadableStream<Uint8Array>({
    start(controller) {
      controller.enqueue(encoder.encode(text))
      controller.close()
    },
  })
}

const createEventEnvelope = (payload: Record<string, unknown> = {}) => ({
  kind: "notification",
  notification_id: "notification-1",
  payload,
  source: "tests",
  topic: "tests",
})

const createResponse = ({
  body,
  ok = true,
  status = 200,
}: {
  body?: ReadableStream<Uint8Array> | null
  ok?: boolean
  status?: number
}) =>
  ({
    body: body ?? null,
    ok,
    status,
  }) as Response

const flushAsync = () =>
  new Promise<void>((resolve) => {
    window.setTimeout(resolve, 0)
  })

describe("user events connection", () => {
  beforeEach(() => {
    vi.useRealTimers()
    localStorage.clear()
    sessionStorage.clear()
    navigation.redirectToLoginWithReturnTo.mockClear()
    OpenAPI.BASE = "https://api.test"
    vi.stubGlobal("fetch", vi.fn())
  })

  test("user_events_connection_parse_sse_text_handles_multiline_comments_retry_and_invalid_json", () => {
    // Arrange / Act
    const events = parseSseText(
      [
        ": keep-alive",
        "id: event-1",
        "event: custom.event",
        "retry: 2500",
        'data: {"one":1}',
        "",
        "id: event-2",
        "event: custom.event",
        "data: {not-json}",
        "data: second-line",
        "",
      ].join("\n"),
    )

    // Assert
    expect(events).toEqual([
      {
        data: '{"one":1}',
        event: "custom.event",
        id: "event-1",
        retry: 2500,
      },
      {
        data: "{not-json}\nsecond-line",
        event: "custom.event",
        id: "event-2",
        retry: null,
      },
    ])
  })

  test("user_events_connection_fetch_uses_token_and_last_event_id", async () => {
    // Arrange
    localStorage.setItem("access_token", "token-123")
    writeUserEventsCursor("user-1", "event-old")
    vi.mocked(fetch).mockResolvedValue(
      createResponse({
        body: createSseStream(""),
      }),
    )
    const connection = new UserEventsConnection()

    // Act
    const release = connection.retain({ userId: "user-1" })
    await flushAsync()
    release()

    // Assert
    expect(fetch).toHaveBeenCalledWith(
      "https://api.test/api/v1/events/stream",
      expect.objectContaining({
        headers: expect.any(Headers),
        method: "GET",
      }),
    )
    const headers = vi.mocked(fetch).mock.calls[0][1]?.headers as Headers
    expect(headers.get("Authorization")).toBe("Bearer token-123")
    expect(headers.get("Last-Event-ID")).toBe("event-old")
  })

  test("user_events_connection_valid_event_emits_listener_and_persists_cursor", async () => {
    // Arrange
    localStorage.setItem("access_token", "token-123")
    vi.mocked(fetch).mockResolvedValue(
      createResponse({
        body: createSseStream(
          [
            "id: event-1",
            "event: account.usage.updated",
            `data: ${JSON.stringify(createEventEnvelope())}`,
            "",
          ].join("\n"),
        ),
      }),
    )
    const connection = new UserEventsConnection()
    const listener = vi.fn()
    connection.subscribe(listener)

    // Act
    const release = connection.retain({ userId: "user-1" })
    await flushAsync()
    release()

    // Assert
    expect(listener).toHaveBeenCalledWith(
      expect.objectContaining({
        id: "event-1",
        name: "account.usage.updated",
      }),
    )
    expect(readUserEventsCursor("user-1")).toBe("event-1")
  })

  test("user_events_connection_unauthorized_redirects_to_login", async () => {
    // Arrange
    localStorage.setItem("access_token", "token-123")
    vi.mocked(fetch).mockResolvedValue(
      createResponse({
        ok: false,
        status: 401,
      }),
    )
    const connection = new UserEventsConnection()

    // Act
    const release = connection.retain({ userId: "user-1" })
    await flushAsync()
    release()

    // Assert
    expect(navigation.redirectToLoginWithReturnTo).toHaveBeenCalled()
  })

  test("user_events_connection_forbidden_does_not_reconnect", async () => {
    // Arrange
    localStorage.setItem("access_token", "token-123")
    vi.mocked(fetch).mockResolvedValue(
      createResponse({
        ok: false,
        status: 403,
      }),
    )
    const connection = new UserEventsConnection()

    // Act
    const release = connection.retain({ userId: "user-1" })
    await flushAsync()
    release()

    // Assert
    expect(fetch).toHaveBeenCalledTimes(1)
  })

  test("user_events_connection_server_error_reconnects_with_fake_timers", async () => {
    // Arrange
    vi.useFakeTimers()
    localStorage.setItem("access_token", "token-123")
    vi.mocked(fetch).mockResolvedValue(
      createResponse({
        ok: false,
        status: 500,
      }),
    )
    const connection = new UserEventsConnection()

    // Act
    const release = connection.retain({ userId: "user-1" })
    await vi.advanceTimersByTimeAsync(1_000)
    release()

    // Assert
    expect(fetch).toHaveBeenCalledTimes(2)
  })

  test("user_events_connection_unretain_aborts_in_flight_request", async () => {
    // Arrange
    localStorage.setItem("access_token", "token-123")
    let capturedSignal: AbortSignal | undefined
    vi.mocked(fetch).mockImplementation((_url, init) => {
      capturedSignal = init?.signal as AbortSignal
      return new Promise<Response>(() => undefined)
    })
    const connection = new UserEventsConnection()

    // Act
    const release = connection.retain({ userId: "user-1" })
    await flushAsync()
    release()

    // Assert
    expect(capturedSignal?.aborted).toBe(true)
  })
})
