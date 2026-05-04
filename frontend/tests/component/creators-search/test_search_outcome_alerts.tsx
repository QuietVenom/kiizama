import { screen } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import { describe, expect, test, vi } from "vitest"

import { SearchOutcomeAlerts } from "../../../src/routes/_layout/-components/creators-search/SearchOutcomeAlerts"
import { renderWithProviders } from "../helpers/render"

const createMutation = (overrides: { isPending?: boolean } = {}) => ({
  isPending: overrides.isPending ?? false,
  mutate: vi.fn(),
})

describe("search outcome alerts", () => {
  test("search_outcome_alerts_search_and_report_errors_render", () => {
    // Arrange / Act
    renderWithProviders(
      <SearchOutcomeAlerts
        expiredJobsError={null}
        expiredJobsMutation={createMutation()}
        expiredUsernames={[]}
        missingJobsError={null}
        missingJobsMutation={createMutation()}
        missingUsernames={[]}
        reportError="Report failed"
        searchError="Search failed"
      />,
    )

    // Assert
    expect(screen.getAllByText("La búsqueda falló")[0]).toBeVisible()
    expect(screen.getByText("La generación del reporte falló")).toBeVisible()
    expect(screen.getByText("Report failed")).toBeVisible()
  })

  test("search_outcome_alerts_expired_usernames_trigger_expired_job", async () => {
    // Arrange
    const user = userEvent.setup()
    const expiredJobsMutation = createMutation()
    renderWithProviders(
      <SearchOutcomeAlerts
        expiredJobsError="Duplicate expired job"
        expiredJobsMutation={expiredJobsMutation}
        expiredUsernames={["expired_creator"]}
        missingJobsError={null}
        missingJobsMutation={createMutation()}
        missingUsernames={[]}
        reportError={null}
        searchError={null}
      />,
    )

    // Act
    await user.click(screen.getByRole("button", { name: "Buscar" }))

    // Assert
    expect(
      screen.getByText("Los perfiles necesitan actualización"),
    ).toBeVisible()
    expect(screen.getByText("@expired_creator")).toBeVisible()
    expect(screen.getByText("Duplicate expired job")).toBeVisible()
    expect(expiredJobsMutation.mutate).toHaveBeenCalledWith(["expired_creator"])
  })

  test("search_outcome_alerts_missing_usernames_trigger_missing_job", async () => {
    // Arrange
    const user = userEvent.setup()
    const missingJobsMutation = createMutation()
    renderWithProviders(
      <SearchOutcomeAlerts
        expiredJobsError={null}
        expiredJobsMutation={createMutation()}
        expiredUsernames={[]}
        missingJobsError="Duplicate missing job"
        missingJobsMutation={missingJobsMutation}
        missingUsernames={["missing_creator"]}
        reportError={null}
        searchError={null}
      />,
    )

    // Act
    await user.click(screen.getByRole("button", { name: "Buscar" }))

    // Assert
    expect(screen.getByText("Usernames no encontrados")).toBeVisible()
    expect(screen.getByText("@missing_creator")).toBeVisible()
    expect(screen.getByText("Duplicate missing job")).toBeVisible()
    expect(missingJobsMutation.mutate).toHaveBeenCalledWith(["missing_creator"])
  })
})
