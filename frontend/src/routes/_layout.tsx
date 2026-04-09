import { Box, Flex } from "@chakra-ui/react"
import {
  createFileRoute,
  Outlet,
  redirect,
  useLocation,
} from "@tanstack/react-router"
import { ApiError, type UserPublic, UsersService } from "@/client"
import Sidebar from "@/components/Common/Sidebar"
import { normalizeAppError } from "@/features/errors/http"
import { buildLoginHrefWithReturnTo } from "@/features/errors/navigation"
import { UserEventsBootstrap } from "@/features/user-events/UserEventsBootstrap"
import { currentUserQueryOptions, isLoggedIn } from "@/hooks/useAuth"

const dashboardShellRoutes = [
  "/overview",
  "/creators-search",
  "/brand-intelligence",
] as const

const usesDashboardShell = (pathname: string) =>
  dashboardShellRoutes.some(
    (route) => pathname === route || pathname.startsWith(`${route}/`),
  )

export const Route = createFileRoute("/_layout")({
  component: Layout,
  beforeLoad: async ({ context, location }) => {
    if (!isLoggedIn()) {
      throw redirect({
        href: buildLoginHrefWithReturnTo(location.href),
      })
    }

    try {
      const currentUser = await UsersService.readUserMe()
      context.queryClient.setQueryData<UserPublic>(
        currentUserQueryOptions.queryKey,
        currentUser,
      )
    } catch (error) {
      if (error instanceof ApiError || error instanceof Error) {
        const normalizedError = normalizeAppError(error, "loader")

        if (normalizedError.status === 401 || normalizedError.status === 403) {
          throw redirect({
            href: buildLoginHrefWithReturnTo(location.href),
          })
        }
      }

      throw error
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
