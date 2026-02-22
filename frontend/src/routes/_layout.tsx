import { Box, Flex } from "@chakra-ui/react"
import {
  createFileRoute,
  Outlet,
  redirect,
  useLocation,
} from "@tanstack/react-router"

import Sidebar from "@/components/Common/Sidebar"
import { isLoggedIn } from "@/hooks/useAuth"

export const Route = createFileRoute("/_layout")({
  component: Layout,
  beforeLoad: async () => {
    if (!isLoggedIn()) {
      throw redirect({
        to: "/login",
      })
    }
  },
})

function Layout() {
  const { pathname } = useLocation()
  const isDashboardRoute = pathname === "/app" || pathname.startsWith("/app/")

  return (
    <Flex h="100vh" overflow="hidden" bg="ui.page">
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
