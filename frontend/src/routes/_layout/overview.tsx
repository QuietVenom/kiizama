import { createFileRoute } from "@tanstack/react-router"

import { billingSummaryQueryOptions } from "@/features/billing/api"
import { OverviewPage } from "./-components/OverviewPage"

export const Route = createFileRoute("/_layout/overview")({
  loader: async ({ context }) => {
    await context.queryClient.fetchQuery(billingSummaryQueryOptions)
  },
  component: OverviewPage,
})
