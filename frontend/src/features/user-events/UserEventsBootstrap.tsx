import { useQuery } from "@tanstack/react-query"
import { useEffect } from "react"

import { currentUserQueryOptions, isLoggedIn } from "@/hooks/useAuth"

import { retainUserEventsConnection, subscribeToUserEvents } from "./connection"
import { applyUserEventEffects } from "./effects"
import { registerToastUserEventEffects } from "./toast-effects"

export const UserEventsBootstrap = () => {
  const { data: currentUser } = useQuery(currentUserQueryOptions)

  useEffect(() => registerToastUserEventEffects(), [])

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
