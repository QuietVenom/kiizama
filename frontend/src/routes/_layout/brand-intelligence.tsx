import { Box, Heading, Text } from "@chakra-ui/react"
import { createFileRoute } from "@tanstack/react-router"

import DashboardTopbar from "@/components/Dashboard/DashboardTopbar"

export const Route = createFileRoute("/_layout/brand-intelligence")({
  component: BrandIntelligencePage,
})

function BrandIntelligencePage() {
  return (
    <Box minH="100vh" bg="ui.page">
      <DashboardTopbar />

      <Box px={{ base: 4, md: 7, lg: 10 }} py={{ base: 7, lg: 9 }}>
        <Box layerStyle="landingCard" p={{ base: 6, md: 8 }}>
          <Heading size="lg">Brand Intelligence</Heading>
          <Text mt={3} color="ui.secondaryText">
            This section is now available. Content will be added here soon.
          </Text>
        </Box>
      </Box>
    </Box>
  )
}
