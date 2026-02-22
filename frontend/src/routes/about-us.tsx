import { Box, Heading, Stack, Text } from "@chakra-ui/react"
import { createFileRoute } from "@tanstack/react-router"
import InfoPageShell from "@/components/Common/InfoPageShell"

export const Route = createFileRoute("/about-us")({
  component: AboutUsPage,
})

function AboutUsPage() {
  return (
    <InfoPageShell>
      <Box
        bg="white"
        borderWidth="1px"
        borderColor="gray.100"
        rounded="3xl"
        p={{ base: 6, md: 10 }}
        boxShadow="0 16px 34px rgba(15, 23, 42, 0.06)"
      >
        <Stack gap={4}>
          <Text
            color="orange.500"
            textTransform="uppercase"
            fontWeight="bold"
            letterSpacing="0.12em"
            fontSize="xs"
          >
            Company
          </Text>
          <Heading
            size={{ base: "2xl", md: "3xl" }}
            color="gray.900"
            letterSpacing="-0.02em"
            fontFamily="'Plus Jakarta Sans', 'Avenir Next', 'Segoe UI', sans-serif"
          >
            About Us
          </Heading>
          <Text color="gray.700" lineHeight="1.8">
            Placeholder content for the About Us page.
          </Text>
        </Stack>
      </Box>
    </InfoPageShell>
  )
}
