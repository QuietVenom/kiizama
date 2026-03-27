import { createFileRoute, redirect } from "@tanstack/react-router"

export const Route = createFileRoute("/_layout/brand-intelligence/")({
  beforeLoad: () => {
    throw redirect({
      to: "/brand-intelligence/reputation-strategy",
    })
  },
  component: () => null,
})
