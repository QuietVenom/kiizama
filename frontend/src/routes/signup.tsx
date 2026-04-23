import { createFileRoute, redirect } from "@tanstack/react-router"

import { ensureValidStoredSession } from "@/features/auth/session"
import { isPublicFeatureFlagEnabled } from "@/hooks/useFeatureFlags"
import { SignUpPage } from "./-components/SignUpPage"

const WAITING_LIST_FLAG_KEY = "waiting-list"

export const Route = createFileRoute("/signup")({
  component: SignUpPage,
  beforeLoad: async () => {
    if (await ensureValidStoredSession()) {
      throw redirect({
        to: "/overview",
      })
    }

    let isWaitingListEnabled = false
    try {
      isWaitingListEnabled = await isPublicFeatureFlagEnabled(
        WAITING_LIST_FLAG_KEY,
      )
    } catch {
      // If flag fetch fails, keep signup available.
    }

    if (isWaitingListEnabled) {
      throw redirect({
        to: "/waiting-list",
      })
    }
  },
})
