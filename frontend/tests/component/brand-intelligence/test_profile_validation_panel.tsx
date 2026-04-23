import { screen } from "@testing-library/react"
import { describe, expect, test } from "vitest"

import type { ProfileExistenceItem } from "../../../src/client"
import ProfileValidationPanel from "../../../src/components/BrandIntelligence/ProfileValidationPanel"
import { renderWithProviders } from "../helpers/render"

const createProfile = (
  overrides: Partial<ProfileExistenceItem> = {},
): ProfileExistenceItem => ({
  exists: true,
  expired: false,
  username: "creator_one",
  ...overrides,
})

describe("profile validation panel", () => {
  test("profile_validation_panel_without_usernames_renders_initial_gate", () => {
    // Arrange / Act
    renderWithProviders(<ProfileValidationPanel profiles={[]} usernames={[]} />)

    // Assert
    expect(screen.getByText("Profile validation gate")).toBeVisible()
    expect(
      screen.getByText(/Add the required creator usernames first/i),
    ).toBeVisible()
  })

  test("profile_validation_panel_loading_without_profiles_renders_loading_state", () => {
    // Arrange / Act
    renderWithProviders(
      <ProfileValidationPanel
        isLoading
        profiles={[]}
        usernames={["creator_one"]}
      />,
    )

    // Assert
    expect(screen.getByText("Validating profiles")).toBeVisible()
  })

  test("profile_validation_panel_error_without_profiles_renders_failure_state", () => {
    // Arrange / Act
    renderWithProviders(
      <ProfileValidationPanel
        error="Unable to validate profiles."
        profiles={[]}
        usernames={["creator_one"]}
      />,
    )

    // Assert
    expect(screen.getByText("Validation failed")).toBeVisible()
    expect(screen.getByText("Unable to validate profiles.")).toBeVisible()
  })

  test("profile_validation_panel_stale_validation_renders_outdated_state", () => {
    // Arrange / Act
    renderWithProviders(
      <ProfileValidationPanel
        isStale
        profiles={[]}
        usernames={["creator_one"]}
      />,
    )

    // Assert
    expect(screen.getByText("Validation is outdated")).toBeVisible()
  })

  test("profile_validation_panel_profiles_render_ready_missing_and_expired_states", () => {
    // Arrange / Act
    renderWithProviders(
      <ProfileValidationPanel
        profiles={[
          createProfile({ username: "ready" }),
          createProfile({ expired: true, username: "expired" }),
          createProfile({ exists: false, username: "missing" }),
        ]}
        usernames={["ready", "expired", "missing"]}
      />,
    )

    // Assert
    expect(screen.getByText("3 checked")).toBeVisible()
    expect(screen.getByText("@ready · Ready")).toBeVisible()
    expect(screen.getByText("@expired · Update Needed")).toBeVisible()
    expect(screen.getByText("@missing · Missing")).toBeVisible()
    expect(
      screen.getByText("consulte los perfiles validados y vuelva a intentar"),
    ).toBeVisible()
  })
})
