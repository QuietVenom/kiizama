import { createFileRoute } from "@tanstack/react-router"

import { billingSummaryQueryOptions } from "@/features/billing/api"
import { CreatorsSearchPage } from "./-components/creators-search/CreatorsSearchPage"

export const Route = createFileRoute("/_layout/creators-search")({
  loader: async ({ context }) => {
    await context.queryClient.fetchQuery(billingSummaryQueryOptions)
  },
  component: CreatorsSearchPage,
})
