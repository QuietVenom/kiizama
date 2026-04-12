import { Box, type BoxProps } from "@chakra-ui/react"
import type { ReactNode } from "react"

import DashboardTopbar from "@/components/Dashboard/DashboardTopbar"

type DashboardPageShellProps = {
  children: ReactNode
  contentProps?: BoxProps
}

const DashboardPageShell = ({
  children,
  contentProps,
}: DashboardPageShellProps) => (
  <Box minH="100vh" bg="ui.page">
    <DashboardTopbar />
    <Box
      px={{ base: 4, md: 7, lg: 10 }}
      py={{ base: 7, lg: 9 }}
      {...contentProps}
    >
      {children}
    </Box>
  </Box>
)

export default DashboardPageShell
