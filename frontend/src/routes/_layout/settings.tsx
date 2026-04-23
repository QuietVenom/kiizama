import { createFileRoute, useNavigate } from "@tanstack/react-router"
import { z } from "zod"

import { billingSummaryQueryOptions } from "@/features/billing/api"
import { UserSettingsPage } from "./-components/UserSettingsPage"

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
  const navigate = useNavigate({ from: Route.fullPath })
  const { billing_return, tab } = Route.useSearch()

  const clearBillingReturn = () => {
    navigate({
      to: "/settings",
      replace: true,
      search: (prev) => ({
        ...prev,
        billing_return: undefined,
      }),
    })
  }

  return (
    <UserSettingsPage
      billingReturn={billing_return}
      onBillingReturnConsumed={clearBillingReturn}
      onTabChange={(value) =>
        navigate({
          to: "/settings",
          search: (prev) => ({
            ...prev,
            billing_return: undefined,
            tab: value === "my-profile" ? undefined : value,
          }),
        })
      }
      tab={tab}
    />
  )
}
