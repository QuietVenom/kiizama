import { Box, Heading, Stack, Table, Text } from "@chakra-ui/react"
import { createFileRoute, Link as RouterLink } from "@tanstack/react-router"
import { useEffect } from "react"
import InfoPageShell from "@/components/Common/InfoPageShell"

export const Route = createFileRoute("/cookie-tables")({
  component: CookieTablesPage,
})

function CookieTablesPage() {
  useEffect(() => {
    window.scrollTo({ top: 0, left: 0, behavior: "auto" })
  }, [])

  return (
    <InfoPageShell maxW="7xl" useSymbolHomeButton>
      <Box
        bg="white"
        borderWidth="1px"
        borderColor="gray.100"
        rounded="3xl"
        p={{ base: 6, md: 10 }}
        boxShadow="0 16px 34px rgba(15, 23, 42, 0.06)"
      >
        <Stack gap={8}>
          <Stack gap={2}>
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
              Kiizama Cookie Tables
            </Heading>
          </Stack>

          <Stack as="section" gap={4}>
            <Text color="gray.700" lineHeight="1.8">
              These Cookie Tables provide additional information about Cookies
              that Kiizama uses on our Website and Services. Only Strictly
              Necessary Cookies are used in our mobile apps.
            </Text>
            <Text color="gray.700" lineHeight="1.8">
              Please refer to our{" "}
              <RouterLink
                to="/cookie-notice"
                style={{ color: "#F97316", textDecoration: "underline" }}
              >
                Cookie Notice
              </RouterLink>{" "}
              for additional information, including instructions for how to
              disable Cookies. If you have any questions about our use of
              Cookies, you can email us at{" "}
              <a
                href="mailto:admin@kiizama.com"
                style={{ color: "#F97316", textDecoration: "underline" }}
              >
                admin@kiizama.com
              </a>
              .
            </Text>
          </Stack>

          <Stack as="section" gap={4}>
            <Heading size="lg">Strictly Necessary Cookies</Heading>
            <Box overflowX="auto">
              <Table.Root size={{ base: "sm", md: "md" }} minW="980px">
                <Table.Header>
                  <Table.Row>
                    <Table.ColumnHeader>Cookie Name</Table.ColumnHeader>
                    <Table.ColumnHeader>Duration</Table.ColumnHeader>
                    <Table.ColumnHeader>Domain</Table.ColumnHeader>
                    <Table.ColumnHeader>Purpose</Table.ColumnHeader>
                    <Table.ColumnHeader>Provider</Table.ColumnHeader>
                  </Table.Row>
                </Table.Header>
                <Table.Body>
                  <Table.Row>
                    <Table.Cell>access_token</Table.Cell>
                    <Table.Cell>session</Table.Cell>
                    <Table.Cell>Local Storage</Table.Cell>
                    <Table.Cell>JWT Authentication</Table.Cell>
                    <Table.Cell>Kiizama</Table.Cell>
                  </Table.Row>
                  <Table.Row>
                    <Table.Cell>notion_cookie_consent</Table.Cell>
                    <Table.Cell>365 days</Table.Cell>
                    <Table.Cell>www.kiizama.com</Table.Cell>
                    <Table.Cell>
                      Used to help remember your cookie consent preferences.
                    </Table.Cell>
                    <Table.Cell>Kiizama</Table.Cell>
                  </Table.Row>
                </Table.Body>
              </Table.Root>
            </Box>
          </Stack>

          <Stack as="section" gap={4}>
            <Heading size="lg">Functional Cookies</Heading>
            <Box overflowX="auto">
              <Table.Root size={{ base: "sm", md: "md" }} minW="980px">
                <Table.Header>
                  <Table.Row>
                    <Table.ColumnHeader>Cookie Name</Table.ColumnHeader>
                    <Table.ColumnHeader>Duration</Table.ColumnHeader>
                    <Table.ColumnHeader>Domain</Table.ColumnHeader>
                    <Table.ColumnHeader>Purpose</Table.ColumnHeader>
                    <Table.ColumnHeader>Provider</Table.ColumnHeader>
                  </Table.Row>
                </Table.Header>
                <Table.Body>
                  <Table.Row>
                    <Table.Cell> </Table.Cell>
                    <Table.Cell> </Table.Cell>
                    <Table.Cell> </Table.Cell>
                    <Table.Cell> </Table.Cell>
                    <Table.Cell> </Table.Cell>
                  </Table.Row>
                </Table.Body>
              </Table.Root>
            </Box>
          </Stack>

          <Stack as="section" gap={4}>
            <Heading size="lg">Analytics Cookies</Heading>
            <Box overflowX="auto">
              <Table.Root size={{ base: "sm", md: "md" }} minW="980px">
                <Table.Header>
                  <Table.Row>
                    <Table.ColumnHeader>Cookie Name</Table.ColumnHeader>
                    <Table.ColumnHeader>Duration</Table.ColumnHeader>
                    <Table.ColumnHeader>Domain</Table.ColumnHeader>
                    <Table.ColumnHeader>Purpose</Table.ColumnHeader>
                    <Table.ColumnHeader>Provider</Table.ColumnHeader>
                  </Table.Row>
                </Table.Header>
                <Table.Body>
                  <Table.Row>
                    <Table.Cell> </Table.Cell>
                    <Table.Cell> </Table.Cell>
                    <Table.Cell> </Table.Cell>
                    <Table.Cell> </Table.Cell>
                    <Table.Cell> </Table.Cell>
                  </Table.Row>
                </Table.Body>
              </Table.Root>
            </Box>
          </Stack>

          <Stack as="section" gap={4}>
            <Heading size="lg">Marketing Cookies</Heading>
            <Box overflowX="auto">
              <Table.Root size={{ base: "sm", md: "md" }} minW="980px">
                <Table.Header>
                  <Table.Row>
                    <Table.ColumnHeader>Cookie Name</Table.ColumnHeader>
                    <Table.ColumnHeader>Duration</Table.ColumnHeader>
                    <Table.ColumnHeader>Domain</Table.ColumnHeader>
                    <Table.ColumnHeader>Purpose</Table.ColumnHeader>
                    <Table.ColumnHeader>Provider</Table.ColumnHeader>
                  </Table.Row>
                </Table.Header>
                <Table.Body>
                  <Table.Row>
                    <Table.Cell> </Table.Cell>
                    <Table.Cell> </Table.Cell>
                    <Table.Cell> </Table.Cell>
                    <Table.Cell> </Table.Cell>
                    <Table.Cell> </Table.Cell>
                  </Table.Row>
                </Table.Body>
              </Table.Root>
            </Box>
          </Stack>

          <Text color="gray.500" fontSize="sm">
            Last Updated: March 1, 2026
          </Text>
        </Stack>
      </Box>
    </InfoPageShell>
  )
}
