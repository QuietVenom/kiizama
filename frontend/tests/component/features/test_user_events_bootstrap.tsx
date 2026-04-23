import { waitFor } from "@testing-library/react"
import { beforeEach, describe, expect, test, vi } from "vitest"

import type { UserEvent } from "../../../src/features/user-events/types"
import { renderWithProviders } from "../helpers/render"

const { auth, connection, effects, toastEffects } = vi.hoisted(() => {
  const registered: Array<(event: UserEvent) => void> = []

  return {
    auth: {
      loggedIn: true,
      user: {
        email: "user@example.com",
        full_name: "Test User",
        id: "user-1",
        is_active: true,
        is_superuser: false,
      },
    },
    connection: {
      retainUserEventsConnection: vi.fn(),
      subscribeToUserEvents: vi.fn(),
    },
    effects: {
      applyUserEventEffects: vi.fn(),
      registered,
      registerUserEventEffect: vi.fn((effect: (event: UserEvent) => void) => {
        registered.push(effect)
        return vi.fn()
      }),
    },
    toastEffects: {
      registerToastUserEventEffects: vi.fn(() => vi.fn()),
    },
  }
})

vi.mock("@/hooks/useAuth", () => ({
  currentUserQueryOptions: {
    queryFn: () => Promise.resolve(auth.user),
    queryKey: ["currentUser"],
    staleTime: 0,
  },
  isLoggedIn: () => auth.loggedIn,
}))

vi.mock("@/features/user-events/connection", () => ({
  retainUserEventsConnection: connection.retainUserEventsConnection,
  subscribeToUserEvents: connection.subscribeToUserEvents,
}))

vi.mock("@/features/user-events/effects", () => ({
  applyUserEventEffects: effects.applyUserEventEffects,
  registerUserEventEffect: effects.registerUserEventEffect,
}))

vi.mock("@/features/user-events/toast-effects", () => ({
  registerToastUserEventEffects: toastEffects.registerToastUserEventEffects,
}))

const { UserEventsBootstrap } = await import(
  "../../../src/features/user-events/UserEventsBootstrap"
)

const createEvent = (name: UserEvent["name"]): UserEvent =>
  ({
    envelope: {
      kind: "notification",
      notification_id: "notification-1",
      payload: {},
      source: "tests",
      topic: "tests",
    },
    id: "event-1",
    name,
  }) as UserEvent

describe("user events bootstrap", () => {
  beforeEach(() => {
    auth.loggedIn = true
    connection.retainUserEventsConnection.mockReset()
    connection.subscribeToUserEvents.mockReset()
    effects.applyUserEventEffects.mockClear()
    effects.registerUserEventEffect.mockClear()
    effects.registered.length = 0
    toastEffects.registerToastUserEventEffects.mockClear()
    connection.retainUserEventsConnection.mockReturnValue(vi.fn())
    connection.subscribeToUserEvents.mockReturnValue(vi.fn())
  })

  test("user_events_bootstrap_logged_in_user_subscribes_and_retains_connection", async () => {
    // Arrange / Act
    const { unmount } = renderWithProviders(<UserEventsBootstrap />)

    // Assert
    await waitFor(() => {
      expect(connection.retainUserEventsConnection).toHaveBeenCalledWith({
        userId: "user-1",
      })
      expect(connection.subscribeToUserEvents).toHaveBeenCalledWith(
        effects.applyUserEventEffects,
      )
      expect(toastEffects.registerToastUserEventEffects).toHaveBeenCalled()
    })
    unmount()
  })

  test("user_events_bootstrap_logged_out_user_does_not_retain_connection", async () => {
    // Arrange
    auth.loggedIn = false

    // Act
    renderWithProviders(<UserEventsBootstrap />)

    // Assert
    await waitFor(() => {
      expect(connection.subscribeToUserEvents).toHaveBeenCalled()
    })
    expect(connection.retainUserEventsConnection).not.toHaveBeenCalled()
  })

  test("user_events_bootstrap_billing_related_events_invalidate_billing_queries", async () => {
    // Arrange
    const { queryClient } = renderWithProviders(<UserEventsBootstrap />)
    const invalidateQueries = vi.spyOn(queryClient, "invalidateQueries")
    await waitFor(() => {
      expect(effects.registerUserEventEffect).toHaveBeenCalled()
    })
    const billingEffect = effects.registered[0]

    // Act
    billingEffect(createEvent("ig-scrape.job.completed"))
    billingEffect(createEvent("account.usage.updated"))
    billingEffect(createEvent("account.subscription.updated"))

    // Assert
    expect(invalidateQueries).toHaveBeenCalledWith({
      queryKey: ["billing", "me"],
    })
    expect(invalidateQueries).toHaveBeenCalledWith({
      queryKey: ["billing", "notices"],
    })
    expect(invalidateQueries).toHaveBeenCalledTimes(6)
  })
})
