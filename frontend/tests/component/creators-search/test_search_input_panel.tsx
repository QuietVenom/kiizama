import { screen } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import { describe, expect, test, vi } from "vitest"

import { SearchInputPanel } from "../../../src/routes/_layout/-components/creators-search/SearchInputPanel"
import { renderWithProviders } from "../helpers/render"

type SearchInputPanelProps = Parameters<typeof SearchInputPanel>[0]

const renderSearchInputPanel = (
  overrides: Partial<SearchInputPanelProps> = {},
) => {
  const props: SearchInputPanelProps = {
    expiredSet: new Set<string>(),
    hasValidationIssue: false,
    invalidSet: new Set<string>(),
    invalidUsernames: [],
    isSearchPending: false,
    isSearchStale: false,
    maxUsernames: 50,
    missingSet: new Set<string>(),
    onMaxExceeded: vi.fn(),
    onOpenHistory: vi.fn(),
    onSearch: vi.fn(),
    onUsernamesChange: vi.fn(),
    usernames: [],
    ...overrides,
  }

  renderWithProviders(<SearchInputPanel {...props} />)
  return props
}

describe("search input panel", () => {
  test("search_input_panel_history_button_visible_without_usernames_and_opens_history", async () => {
    // Arrange
    const user = userEvent.setup()
    const props = renderSearchInputPanel()

    // Act
    await user.click(screen.getByRole("button", { name: "Historial" }))

    // Assert
    expect(props.onOpenHistory).toHaveBeenCalledTimes(1)
  })

  test("search_input_panel_clear_button_disabled_without_usernames", () => {
    // Arrange / Act
    renderSearchInputPanel()

    // Assert
    expect(screen.getByRole("button", { name: "Limpiar" })).toBeDisabled()
  })

  test("search_input_panel_clear_button_empties_usernames", async () => {
    // Arrange
    const user = userEvent.setup()
    const props = renderSearchInputPanel({ usernames: ["alpha", "beta"] })

    // Act
    await user.click(screen.getByRole("button", { name: "Limpiar" }))

    // Assert
    expect(props.onUsernamesChange).toHaveBeenCalledWith([])
  })
})
