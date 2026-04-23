import { createFileRoute, redirect } from "@tanstack/react-router"

import { ensureValidStoredSession } from "@/features/auth/session"
import { ResetPasswordPage } from "./-components/ResetPasswordPage"

export const Route = createFileRoute("/reset-password")({
  component: ResetPasswordPage,
  beforeLoad: async () => {
    if (await ensureValidStoredSession()) {
      throw redirect({
        to: "/overview",
      })
    }
  },
})
