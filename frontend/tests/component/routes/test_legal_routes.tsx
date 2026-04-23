import { screen } from "@testing-library/react"
import type { ReactNode } from "react"
import { beforeEach, describe, expect, test, vi } from "vitest"

import { renderWithProviders } from "../helpers/render"

vi.mock("@tanstack/react-router", () => ({
  createFileRoute: () => (options: unknown) => options,
  Link: ({ children, to }: { children: ReactNode; to: string }) => (
    <a href={to}>{children}</a>
  ),
}))

const { CookieTablesPage } = await import(
  "../../../src/routes/-components/CookieTablesPage"
)
const { ProvidersPage } = await import(
  "../../../src/routes/-components/ProvidersPage"
)

describe("legal route content", () => {
  beforeEach(() => {
    window.scrollTo = vi.fn()
  })

  test("cookie_tables_route_documents_current_browser_storage", () => {
    renderWithProviders(<CookieTablesPage />)

    expect(screen.getByText("kiizama-creators-search-jobs")).toBeVisible()
    expect(screen.getByText("user-events:last-event-id")).toBeVisible()
    expect(
      screen.getByText(/maintain a consistent user experience/i),
    ).toBeVisible()
    expect(
      screen.getByText(/support continuity for in-session service updates/i),
    ).toBeVisible()
  })

  test("providers_route_documents_apify_integration", () => {
    renderWithProviders(<ProvidersPage />)

    expect(screen.getByText("Apify")).toBeVisible()
    expect(
      screen.getByText("Extracción de perfiles públicos de Instagram"),
    ).toBeVisible()
    expect(
      screen.getByText(/datos públicos devueltos por Instagram/i),
    ).toBeVisible()
  })
})
