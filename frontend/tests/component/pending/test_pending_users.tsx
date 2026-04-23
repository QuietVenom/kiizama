import { screen } from "@testing-library/react"
import { describe, expect, test } from "vitest"

import PendingUsers from "../../../src/components/Pending/PendingUsers"
import { renderWithProviders } from "../helpers/render"

describe("pending users table", () => {
  test("pending_users_loading_state_renders_headers_and_skeleton_rows", () => {
    // Arrange / Act
    renderWithProviders(<PendingUsers />)

    // Assert
    expect(
      screen.getByRole("columnheader", { name: "Full name" }),
    ).toBeVisible()
    expect(screen.getByRole("columnheader", { name: "Email" })).toBeVisible()
    expect(screen.getByRole("columnheader", { name: "Role" })).toBeVisible()
    expect(screen.getByRole("columnheader", { name: "Status" })).toBeVisible()
    expect(screen.getByRole("columnheader", { name: "Actions" })).toBeVisible()
    expect(screen.getAllByRole("row")).toHaveLength(6)
  })
})
