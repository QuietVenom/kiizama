import { Box, Heading, Stack, Text } from "@chakra-ui/react"
import { createFileRoute } from "@tanstack/react-router"
import InfoPageShell from "@/components/Common/InfoPageShell"

export const Route = createFileRoute("/security")({
  component: SecurityPage,
})

function SecurityPage() {
  return (
    <InfoPageShell useSymbolHomeButton>
      <Box layerStyle="infoCard" p={{ base: 6, md: 10 }}>
        <Stack gap={4}>
          <Text textStyle="eyebrow">Company</Text>
          <Heading size={{ base: "2xl", md: "3xl" }} textStyle="pageTitle">
            Security
          </Heading>
          <Text textStyle="pageBody">
            Placeholder content for the Security page.
          </Text>
        </Stack>
      </Box>
    </InfoPageShell>
  )
}
