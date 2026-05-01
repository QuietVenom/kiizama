import { Box, Heading, Tabs } from "@chakra-ui/react"

import DashboardPageShell from "@/components/Dashboard/DashboardPageShell"
import Appearance from "@/components/UserSettings/Appearance"
import ChangePassword from "@/components/UserSettings/ChangePassword"
import DeleteAccount from "@/components/UserSettings/DeleteAccount"
import Payments from "@/components/UserSettings/Payments"
import UserInformation from "@/components/UserSettings/UserInformation"
import useAuth from "@/hooks/useAuth"

const tabsConfig = [
  { value: "my-profile", title: "My profile", component: UserInformation },
  { value: "payments", title: "Payments", component: Payments },
  { value: "password", title: "Password", component: ChangePassword },
  { value: "appearance", title: "Appearance", component: Appearance },
  { value: "danger-zone", title: "Danger zone", component: DeleteAccount },
]

type UserSettingsPageProps = {
  billingReturn?: number
  onBillingReturnConsumed?: () => void
  onTabChange?: (value: string) => void
  tab?: string
}

export function UserSettingsPage({
  billingReturn,
  onBillingReturnConsumed = () => undefined,
  onTabChange = () => undefined,
  tab,
}: UserSettingsPageProps) {
  const { user: currentUser } = useAuth()
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
          onValueChange={({ value }) => onTabChange(value)}
          variant="subtle"
        >
          <Tabs.List>
            {finalTabs.map((tabItem) => (
              <Tabs.Trigger key={tabItem.value} value={tabItem.value}>
                {tabItem.title}
              </Tabs.Trigger>
            ))}
          </Tabs.List>
          {finalTabs.map((tabItem) => {
            const Component = tabItem.component

            return (
              <Tabs.Content key={tabItem.value} value={tabItem.value}>
                {tabItem.value === "payments" ? (
                  <Payments
                    billingReturn={billingReturn}
                    onBillingReturnConsumed={onBillingReturnConsumed}
                  />
                ) : (
                  <Component />
                )}
              </Tabs.Content>
            )
          })}
        </Tabs.Root>
      </Box>
    </DashboardPageShell>
  )
}
