import { Box, type BoxProps } from "@chakra-ui/react"
import type { ReactNode } from "react"
import { boundedContent } from "@/components/Responsive/layout"

type DashboardPageShellProps = {
  children: ReactNode
  contentProps?: BoxProps
}

const DashboardPageShell = ({
  children,
  contentProps,
}: DashboardPageShellProps) => (
  <Box
    {...boundedContent}
    css={{ containerType: "inline-size", containerName: "page" }}
  >
    <Box
      minW={0}
      px={{ base: 4, md: 7, lg: 10 }}
      py={{ base: 7, lg: 9 }}
      {...contentProps}
    >
      {children}
    </Box>
  </Box>
)
export default DashboardPageShell
