import { createFileRoute, redirect } from "@tanstack/react-router"

import { ensureValidStoredSession } from "@/features/auth/session"
import { RecoverPasswordPage } from "./-components/RecoverPasswordPage"

export const Route = createFileRoute("/recover-password")({
  component: RecoverPasswordPage,
  beforeLoad: async () => {
    if (await ensureValidStoredSession()) {
      throw redirect({
        to: "/overview",
      })
    }
  },
})
