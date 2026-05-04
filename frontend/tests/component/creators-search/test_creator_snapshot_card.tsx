import { screen } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import { describe, expect, test, vi } from "vitest"

import type { Profile, ProfileSnapshotExpanded } from "../../../src/client"
import CreatorSnapshotCard from "../../../src/components/CreatorsSearch/CreatorSnapshotCard"
import { renderWithProviders } from "../helpers/render"

const createProfile = (overrides: Partial<Profile> = {}): Profile => ({
  _id: "profile-1",
  ai_categories: ["Fitness"],
  ai_roles: ["Coach"],
  biography: "Fitness and wellness creator.",
  external_url: "https://creator.test",
  follower_count: 12500,
  following_count: 250,
  full_name: "Creator One",
  ig_id: "ig-1",
  is_private: true,
  is_verified: true,
  media_count: 88,
  profile_pic_url: "https://images.test/avatar.jpg",
  updated_date: "2026-01-01T00:00:00Z",
  username: "creator_one",
  ...overrides,
})

const createSnapshot = (
  overrides: Partial<ProfileSnapshotExpanded> = {},
): ProfileSnapshotExpanded =>
  ({
    _id: "snapshot-1",
    metrics_id: "metrics-1",
    post_ids: [],
    profile: createProfile(),
    profile_id: "profile-1",
    reel_ids: [],
    scraped_at: "2026-01-15T00:00:00Z",
    ...overrides,
  }) as ProfileSnapshotExpanded

describe("creator snapshot card", () => {
  test("creator_snapshot_card_profile_data_metrics_and_badges_render", () => {
    // Arrange / Act
    renderWithProviders(
      <CreatorSnapshotCard
        onGenerateReport={vi.fn()}
        onOpenDetails={vi.fn()}
        snapshot={createSnapshot()}
      />,
    )

    // Assert
    expect(screen.getByText("Creator One")).toBeVisible()
    expect(screen.getByText("@creator_one")).toBeVisible()
    expect(screen.getByText("Verificado")).toBeVisible()
    expect(screen.getByText("Privado")).toBeVisible()
    expect(screen.getByText("Fitness")).toBeVisible()
    expect(screen.getByText("Coach")).toBeVisible()
    expect(screen.getByText("12,5 mil")).toBeVisible()
    expect(screen.getByText("250")).toBeVisible()
    expect(screen.getByText("88")).toBeVisible()
  })

  test("creator_snapshot_card_missing_metrics_and_image_use_zero_and_initials", () => {
    // Arrange / Act
    renderWithProviders(
      <CreatorSnapshotCard
        onOpenDetails={vi.fn()}
        snapshot={createSnapshot({
          profile: createProfile({
            follower_count: null as unknown as number,
            following_count: undefined as unknown as number,
            full_name: "",
            media_count: null as unknown as number,
            profile_pic_url: "",
            username: "fallback_user",
          }),
        })}
      />,
    )

    // Assert
    expect(screen.getAllByText("0")).toHaveLength(3)
    expect(screen.getByText("F")).toBeVisible()
  })

  test("creator_snapshot_card_actions_call_report_and_detail_handlers", async () => {
    // Arrange
    const user = userEvent.setup()
    const onGenerateReport = vi.fn()
    const onOpenDetails = vi.fn()
    renderWithProviders(
      <CreatorSnapshotCard
        onGenerateReport={onGenerateReport}
        onOpenDetails={onOpenDetails}
        snapshot={createSnapshot()}
      />,
    )

    // Act
    await user.click(screen.getByRole("button", { name: "Reporte" }))
    await user.click(screen.getByRole("button", { name: "Ver detalle" }))

    // Assert
    expect(onGenerateReport).toHaveBeenCalled()
    expect(onOpenDetails).toHaveBeenCalled()
  })
})
