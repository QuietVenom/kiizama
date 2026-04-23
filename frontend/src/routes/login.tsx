import { createFileRoute, redirect } from "@tanstack/react-router"

import { ensureValidStoredSession } from "@/features/auth/session"
import { getReturnToFromHref } from "@/features/errors/navigation"
import { LoginPage } from "./-components/LoginPage"

export const Route = createFileRoute("/login")({
  component: LoginPage,
  beforeLoad: async ({ location }) => {
    if (await ensureValidStoredSession()) {
      throw redirect({
        href: getReturnToFromHref(location.href) || "/overview",
      })
    }
  },
})
