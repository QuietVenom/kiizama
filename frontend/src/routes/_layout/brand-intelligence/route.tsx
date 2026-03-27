import { createFileRoute, Outlet } from "@tanstack/react-router"

export const Route = createFileRoute("/_layout/brand-intelligence")({
  component: BrandIntelligenceLayout,
})

function BrandIntelligenceLayout() {
  return <Outlet />
}
