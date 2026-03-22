import { Box, Flex } from "@chakra-ui/react"
import {
  createFileRoute,
  Outlet,
  redirect,
  useLocation,
} from "@tanstack/react-router"

import Sidebar from "@/components/Common/Sidebar"
import { UserEventsBootstrap } from "@/features/user-events/UserEventsBootstrap"
import { currentUserQueryOptions, isLoggedIn } from "@/hooks/useAuth"

const dashboardShellRoutes = [
  "/app",
  "/creators-search",
  "/brand-intelligence",
] as const

const usesDashboardShell = (pathname: string) =>
  dashboardShellRoutes.some(
    (route) => pathname === route || pathname.startsWith(`${route}/`),
  )

export const Route = createFileRoute("/_layout")({
  component: Layout,
  beforeLoad: async ({ context }) => {
    if (!isLoggedIn()) {
      throw redirect({
        to: "/login",
      })
    }

    try {
      await context.queryClient.ensureQueryData(currentUserQueryOptions)
    } catch {
      if (!isLoggedIn()) {
        throw redirect({
          to: "/login",
        })
      }
    }
  },
})

function Layout() {
  const { pathname } = useLocation()
  const isDashboardRoute = usesDashboardShell(pathname)

  return (
    <Flex h="100vh" overflow="hidden" bg="ui.page">
      <UserEventsBootstrap />
      <Sidebar />
      <Box flex={1} minW={0}>
        <Flex
          flex={1}
          h="full"
          direction="column"
          p={isDashboardRoute ? 0 : 4}
          overflowY="auto"
          bg={isDashboardRoute ? "ui.page" : "transparent"}
        >
          <Outlet />
        </Flex>
      </Box>
    </Flex>
  )
}
