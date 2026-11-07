import { Tabs } from "@chakra-ui/react"
import { screen } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import { useState } from "react"
import { describe, expect, test } from "vitest"
import { AdaptivePagination } from "../../../src/components/Responsive/AdaptivePagination"
import { ResponsiveTabsList } from "../../../src/components/Responsive/ResponsiveTabsList"
import { WideContent } from "../../../src/components/Responsive/WideContent"
import { renderWithProviders } from "../helpers/render"

function PaginatedResults() {
  const [page, setPage] = useState(1)
  return (
    <AdaptivePagination
      count={3}
      pageSize={1}
      page={page}
      onPageChange={(e) => setPage(e.page)}
    />
  )
}

describe("responsive navigation", () => {
  test.each([
    {
      language: "en",
      previous: "Previous page",
      next: "Next page",
      first: "1 of 3",
      last: "3 of 3",
    },
    {
      language: "es",
      previous: "Página anterior",
      next: "Página siguiente",
      first: "1 de 3",
      last: "3 de 3",
    },
    {
      language: "pt-BR",
      previous: "Página anterior",
      next: "Próxima página",
      first: "1 de 3",
      last: "3 de 3",
    },
  ] as const)(
    "pagination_$language_preserves_page_and_disables_boundaries",
    async ({ language, previous, next, first, last }) => {
      // Arrange
      const user = userEvent.setup()
      renderWithProviders(<PaginatedResults />, { language })
      expect(screen.getByText(first)).toBeVisible()
      expect(screen.getByRole("button", { name: previous })).toBeDisabled()
      // Act
      await user.click(screen.getByRole("button", { name: next }))
      await user.click(screen.getByRole("button", { name: next }))
      // Assert
      expect(screen.getByText(last)).toBeVisible()
      expect(screen.getByRole("button", { name: next })).toBeDisabled()
      await user.click(screen.getByRole("button", { name: previous }))
      expect(screen.getByRole("button", { name: next })).toBeEnabled()
    },
  )

  test("tabs_selection_preserves_semantics", async () => {
    // Arrange
    const user = userEvent.setup()
    renderWithProviders(
      <Tabs.Root defaultValue="first">
        <ResponsiveTabsList>
          <Tabs.Trigger value="first">First</Tabs.Trigger>
          <Tabs.Trigger value="last">Last</Tabs.Trigger>
        </ResponsiveTabsList>
        <Tabs.Content value="first">First panel</Tabs.Content>
        <Tabs.Content value="last">Last panel</Tabs.Content>
      </Tabs.Root>,
    )
    // Act
    await user.click(screen.getByRole("tab", { name: "First" }))
    await user.click(screen.getByRole("tab", { name: "Last" }))
    // Assert
    expect(screen.getByRole("tab", { name: "Last" })).toHaveAttribute(
      "aria-selected",
      "true",
    )
    expect(screen.getByRole("tabpanel", { name: "Last" })).toBeVisible()
  })

  test("wide_content_is_a_named_keyboard_reachable_region", async () => {
    // Arrange
    const user = userEvent.setup()
    renderWithProviders(
      <WideContent label="Creator metrics">
        <table>
          <tbody>
            <tr>
              <td>Followers</td>
            </tr>
          </tbody>
        </table>
      </WideContent>,
    )
    // Act
    await user.tab()
    // Assert
    expect(
      screen.getByRole("region", { name: "Creator metrics" }),
    ).toHaveFocus()
    expect(screen.getByRole("table")).toBeVisible()
  })
})
