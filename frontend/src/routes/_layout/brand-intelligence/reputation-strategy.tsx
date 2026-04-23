import { createFileRoute } from "@tanstack/react-router"

import { ReputationStrategyPage } from "./-components/ReputationStrategyPage"

export const Route = createFileRoute(
  "/_layout/brand-intelligence/reputation-strategy",
)({
  component: ReputationStrategyPage,
})
