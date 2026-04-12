import { Box, Heading, Tabs } from "@chakra-ui/react"
import { createFileRoute, useNavigate } from "@tanstack/react-router"
import { z } from "zod"

import DashboardPageShell from "@/components/Dashboard/DashboardPageShell"
import Appearance from "@/components/UserSettings/Appearance"
import ChangePassword from "@/components/UserSettings/ChangePassword"
import DeleteAccount from "@/components/UserSettings/DeleteAccount"
import Payments from "@/components/UserSettings/Payments"
import UserInformation from "@/components/UserSettings/UserInformation"
import { billingSummaryQueryOptions } from "@/features/billing/api"
import useAuth from "@/hooks/useAuth"

const tabsConfig = [
  { value: "my-profile", title: "My profile", component: UserInformation },
  { value: "payments", title: "Payments", component: Payments },
  { value: "password", title: "Password", component: ChangePassword },
  { value: "appearance", title: "Appearance", component: Appearance },
  { value: "danger-zone", title: "Danger zone", component: DeleteAccount },
]

const settingsSearchSchema = z.object({
  billing_return: z.number().optional().catch(undefined),
  tab: z.string().optional().catch(undefined),
})

export const Route = createFileRoute("/_layout/settings")({
  loader: async ({ context }) => {
    await context.queryClient.fetchQuery(billingSummaryQueryOptions)
  },
  component: UserSettings,
  validateSearch: (search) => settingsSearchSchema.parse(search),
})

function UserSettings() {
  const { user: currentUser } = useAuth()
  const navigate = useNavigate({ from: Route.fullPath })
  const { tab } = Route.useSearch()
  const finalTabs = currentUser?.is_superuser
    ? tabsConfig.filter(
        (item) => item.value !== "payments" && item.value !== "danger-zone",
      )
    : tabsConfig
  const availableTabs = new Set(finalTabs.map((item) => item.value))
  const activeTab = tab && availableTabs.has(tab) ? tab : "my-profile"

  if (!currentUser) {
    return null
  }

  return (
    <DashboardPageShell>
      <Box>
        <Heading size="lg" textAlign={{ base: "center", md: "left" }} mb={8}>
          User Settings
        </Heading>

        <Tabs.Root
          value={activeTab}
          onValueChange={({ value }) =>
            navigate({
              to: "/settings",
              search: (prev) => ({
                ...prev,
                billing_return: undefined,
                tab: value === "my-profile" ? undefined : value,
              }),
            })
          }
          variant="subtle"
        >
          <Tabs.List>
            {finalTabs.map((tab) => (
              <Tabs.Trigger key={tab.value} value={tab.value}>
                {tab.title}
              </Tabs.Trigger>
            ))}
          </Tabs.List>
          {finalTabs.map((tab) => (
            <Tabs.Content key={tab.value} value={tab.value}>
              <tab.component />
            </Tabs.Content>
          ))}
        </Tabs.Root>
      </Box>
    </DashboardPageShell>
  )
}
