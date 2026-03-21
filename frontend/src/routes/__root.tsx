import type { QueryClient } from "@tanstack/react-query"
import { createRootRouteWithContext, Outlet } from "@tanstack/react-router"
import { lazy, Suspense } from "react"

import CookieConsentPrompt from "@/components/Common/CookieConsentPrompt"
import NotFound from "@/components/Common/NotFound"

export interface RouterAppContext {
  queryClient: QueryClient
}

const loadDevtools = () =>
  Promise.all([
    import("@tanstack/router-devtools"),
    import("@tanstack/react-query-devtools"),
  ]).then(([routerDevtools, reactQueryDevtools]) => {
    return {
      default: () => (
        <>
          <routerDevtools.TanStackRouterDevtools />
          <reactQueryDevtools.ReactQueryDevtools />
        </>
      ),
    }
  })

const TanStackDevtools = import.meta.env.PROD ? () => null : lazy(loadDevtools)

export const Route = createRootRouteWithContext<RouterAppContext>()({
  component: () => (
    <>
      <Outlet />
      <CookieConsentPrompt />
      <Suspense>
        <TanStackDevtools />
      </Suspense>
    </>
  ),
  notFoundComponent: () => <NotFound />,
})
