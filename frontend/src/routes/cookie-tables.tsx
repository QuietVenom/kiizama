import { createFileRoute } from "@tanstack/react-router"
import { CookieTablesPage } from "./-components/CookieTablesPage"

export const Route = createFileRoute("/cookie-tables")({
  component: CookieTablesPage,
})
