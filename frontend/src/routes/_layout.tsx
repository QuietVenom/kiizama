import { Box, Flex } from "@chakra-ui/react"
import {
  createFileRoute,
  Outlet,
  redirect,
  useLocation,
} from "@tanstack/react-router"
import { useId, useRef, useState } from "react"
import { ApiError, type UserPublic, UsersService } from "@/client"
import Sidebar from "@/components/Common/Sidebar"
import DashboardTopbar from "@/components/Dashboard/DashboardTopbar"
import { normalizeAppError } from "@/features/errors/http"
import { buildLoginHrefWithReturnTo } from "@/features/errors/navigation"
import { UserEventsBootstrap } from "@/features/user-events/UserEventsBootstrap"
import { currentUserQueryOptions, isLoggedIn } from "@/hooks/useAuth"

const dashboardShellRoutes = [
  "/overview",
  "/creators-search",
  "/brand-intelligence",
  "/settings",
  "/admin",
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
  const [menuOpen, setMenuOpen] = useState(false)
  const navigationId = useId()
  const menuTriggerRef = useRef<HTMLButtonElement>(null)

  return (
    <Flex h="100vh" css={{ height: "100dvh" }} overflow="hidden" bg="ui.page">
      <UserEventsBootstrap />
      <Sidebar
        navigationId={navigationId}
        open={menuOpen}
        onOpenChange={setMenuOpen}
        showTrigger={false}
        triggerRef={menuTriggerRef}
      />
      <Box
        flex={1}
        minW={0}
        css={{ containerType: "inline-size", containerName: "shell" }}
      >
        <Flex h="full" minW={0} minH={0} direction="column">
          {isDashboardRoute ? (
            <DashboardTopbar
              navigationId={navigationId}
              menuOpen={menuOpen}
              onOpenMenu={() => setMenuOpen(true)}
              menuTriggerRef={menuTriggerRef}
            />
          ) : null}
          <Box
            as="main"
            data-testid="app-scroll"
            flex={1}
            minH={0}
            minW={0}
            overflowY="auto"
            bg="ui.page"
          >
            <Outlet />
          </Box>
        </Flex>
      </Box>
    </Flex>
  )
}
