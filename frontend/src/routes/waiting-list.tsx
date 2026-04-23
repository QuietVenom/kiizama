import { createFileRoute, redirect } from "@tanstack/react-router"

import { ensureValidStoredSession } from "@/features/auth/session"
import { WaitingListPage } from "./-components/WaitingListPage"

export const Route = createFileRoute("/waiting-list")({
  component: WaitingListPage,
  beforeLoad: async () => {
    if (await ensureValidStoredSession()) {
      throw redirect({
        to: "/overview",
      })
    }
  },
})
