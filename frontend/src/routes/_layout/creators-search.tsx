import { createFileRoute } from "@tanstack/react-router"

import { CreatorsSearchPage } from "./-components/creators-search/CreatorsSearchPage"

export const Route = createFileRoute("/_layout/creators-search")({
  component: CreatorsSearchPage,
})
