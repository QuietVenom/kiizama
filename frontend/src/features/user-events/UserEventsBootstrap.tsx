import { useQuery, useQueryClient } from "@tanstack/react-query"
import { useEffect } from "react"

import {
  billingNoticesQueryKey,
  billingSummaryQueryKey,
} from "@/features/billing/api"
import { currentUserQueryOptions, isLoggedIn } from "@/hooks/useAuth"

import { retainUserEventsConnection, subscribeToUserEvents } from "./connection"
import { applyUserEventEffects, registerUserEventEffect } from "./effects"
import { registerToastUserEventEffects } from "./toast-effects"

export const UserEventsBootstrap = () => {
  const queryClient = useQueryClient()
  const { data: currentUser } = useQuery(currentUserQueryOptions)

  useEffect(() => registerToastUserEventEffects(), [])

  useEffect(
    () =>
      registerUserEventEffect((event) => {
        if (
          event.name === "ig-scrape.job.completed" ||
          event.name === "account.usage.updated" ||
          event.name === "account.subscription.updated"
        ) {
          void queryClient.invalidateQueries({
            queryKey: billingSummaryQueryKey,
          })
          void queryClient.invalidateQueries({
            queryKey: billingNoticesQueryKey,
          })
        }
      }),
    [queryClient],
  )

  useEffect(() => subscribeToUserEvents(applyUserEventEffects), [])

  useEffect(() => {
    if (!currentUser?.id || !isLoggedIn()) {
      return
    }

    return retainUserEventsConnection({
      userId: currentUser.id,
    })
  }, [currentUser?.id])

  return null
}
