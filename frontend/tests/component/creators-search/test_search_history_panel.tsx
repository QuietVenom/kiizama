import { screen } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import { describe, expect, test, vi } from "vitest"

import type { CreatorsSearchHistoryItem } from "../../../src/client"
import { SearchHistoryPanel } from "../../../src/routes/_layout/-components/creators-search/SearchHistoryPanel"
import { renderWithProviders } from "../helpers/render"

const createHistoryItem = (
  overrides: Partial<CreatorsSearchHistoryItem> = {},
): CreatorsSearchHistoryItem => ({
  created_at: "2026-04-25T00:00:00Z",
  id: "history_123",
  job_id: "job_123",
  ready_usernames: ["alpha", "beta"],
  source: "ig-scrape-job",
  ...overrides,
})

describe("search history panel", () => {
  test("search_history_panel_loading_state_hides_empty_and_error_messages", () => {
    // Arrange / Act
    renderWithProviders(
      <SearchHistoryPanel
        isError={false}
        isLoading
        items={[]}
        onReuseReadyUsernames={vi.fn()}
        onViewAll={vi.fn()}
      />,
    )

    // Assert
    expect(screen.getByText("Search history")).toBeVisible()
    expect(screen.queryByText("No search history available yet.")).toBeNull()
    expect(
      screen.queryByText("Search history is temporarily unavailable."),
    ).toBeNull()
  })

  test("search_history_panel_error_state_renders_unavailable_message", () => {
    // Arrange / Act
    renderWithProviders(
      <SearchHistoryPanel
        isError
        isLoading={false}
        items={[]}
        onReuseReadyUsernames={vi.fn()}
        onViewAll={vi.fn()}
      />,
    )

    // Assert
    expect(
      screen.getByText("Search history is temporarily unavailable."),
    ).toBeVisible()
  })

  test("search_history_panel_empty_state_renders_empty_message", () => {
    // Arrange / Act
    renderWithProviders(
      <SearchHistoryPanel
        isError={false}
        isLoading={false}
        items={[]}
        onReuseReadyUsernames={vi.fn()}
        onViewAll={vi.fn()}
      />,
    )

    // Assert
    expect(screen.getByText("No search history available yet.")).toBeVisible()
  })

  test("search_history_panel_populated_preview_reuses_ready_usernames", async () => {
    // Arrange
    const user = userEvent.setup()
    const onReuseReadyUsernames = vi.fn()
    const onViewAll = vi.fn()
    renderWithProviders(
      <SearchHistoryPanel
        isError={false}
        isLoading={false}
        items={[createHistoryItem()]}
        onReuseReadyUsernames={onReuseReadyUsernames}
        onViewAll={onViewAll}
      />,
    )

    // Act
    await user.click(screen.getByRole("button", { name: /job_123/i }))
    await user.click(screen.getByRole("button", { name: "View all" }))

    // Assert
    expect(onReuseReadyUsernames).toHaveBeenCalledWith(["alpha", "beta"])
    expect(onViewAll).toHaveBeenCalled()
  })
})
