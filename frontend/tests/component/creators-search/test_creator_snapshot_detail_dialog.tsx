import { screen } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import { describe, expect, test, vi } from "vitest"

import type { ProfileSnapshotExpanded } from "../../../src/client"
import CreatorSnapshotDetailDialog from "../../../src/components/CreatorsSearch/CreatorSnapshotDetailDialog"
import { renderWithProviders } from "../helpers/render"

const createSnapshot = (
  overrides: Partial<ProfileSnapshotExpanded> = {},
): ProfileSnapshotExpanded =>
  ({
    _id: "snapshot-1",
    metrics: {
      _id: "metrics-1",
      overall_post_engagement_rate: 0.08,
      post_metrics: {
        avg_comments: 10,
        avg_engagement_rate: 0.08,
        avg_likes: 100,
        hashtags_per_post: 2,
        mentions_per_post: 1,
        total_comments: 20,
        total_likes: 200,
        total_posts: 2,
      },
      reel_engagement_rate_on_plays: 0.12,
      reel_metrics: {
        avg_plays: 1000,
        avg_reel_comments: 20,
        avg_reel_likes: 120,
        total_plays: 2000,
        total_reels: 2,
      },
    },
    metrics_id: "metrics-1",
    post_ids: ["post-1"],
    posts: [
      {
        profile_id: "profile-1",
        posts: [
          {
            caption_text: "Post caption",
            code: "POST1",
            comment_count: 10,
            like_count: 100,
            media_type: 1,
          },
        ],
        updated_at: "2026-01-16T00:00:00Z",
      },
    ],
    profile: {
      _id: "profile-1",
      ai_categories: ["Fitness"],
      ai_roles: ["Coach"],
      bio_links: [
        { title: "Shop", url: "https://creator.test/shop" },
        { title: "Shop duplicate", url: "https://creator.test/shop" },
      ],
      biography: "Fitness and wellness creator.",
      external_url: "https://creator.test",
      follower_count: 12500,
      following_count: 250,
      full_name: "Creator One",
      ig_id: "ig-1",
      is_private: false,
      is_verified: true,
      media_count: 88,
      profile_pic_url: "",
      updated_date: "2026-01-01T00:00:00Z",
      username: "creator_one",
    },
    profile_id: "profile-1",
    reel_ids: ["reel-1"],
    reels: [
      {
        profile_id: "profile-1",
        reels: [
          {
            code: "REEL1",
            comment_count: 20,
            like_count: 120,
            media_type: 2,
            play_count: 1000,
            product_type: "clips",
          },
        ],
        updated_at: "2026-01-16T00:00:00Z",
      },
    ],
    scraped_at: "2026-01-15T00:00:00Z",
    ...overrides,
  }) as ProfileSnapshotExpanded

describe("creator snapshot detail dialog", () => {
  test("creator_snapshot_detail_dialog_closed_snapshot_renders_no_dialog_content", () => {
    // Arrange / Act
    renderWithProviders(
      <CreatorSnapshotDetailDialog onOpenChange={vi.fn()} snapshot={null} />,
    )

    // Assert
    expect(
      screen.queryByText("Detalle del snapshot del creador"),
    ).not.toBeInTheDocument()
  })

  test("creator_snapshot_detail_dialog_open_snapshot_renders_profile_metrics_and_sections", () => {
    // Arrange / Act
    renderWithProviders(
      <CreatorSnapshotDetailDialog
        onOpenChange={vi.fn()}
        snapshot={createSnapshot()}
      />,
    )

    // Assert
    expect(screen.getAllByText("Creator One")[0]).toBeVisible()
    expect(screen.getAllByText(/@creator_one/)[0]).toBeVisible()
    expect(screen.getByText("Análisis de IA")).toBeVisible()
    expect(screen.getByText("Métricas")).toBeVisible()
    expect(screen.getByText("Posts (1)")).toBeVisible()
    expect(screen.getByText("Reels (1)")).toBeVisible()
    expect(screen.getByText("Fitness")).toBeVisible()
    expect(screen.getByText("Coach")).toBeVisible()
    expect(screen.getByText("Posts totales")).toBeVisible()
    expect(screen.getByText("Reels totales")).toBeVisible()
  })

  test("creator_snapshot_detail_dialog_empty_posts_reels_and_metrics_render_empty_copy", () => {
    // Arrange / Act
    renderWithProviders(
      <CreatorSnapshotDetailDialog
        onOpenChange={vi.fn()}
        snapshot={createSnapshot({
          metrics: null,
          posts: [],
          reels: [],
        })}
      />,
    )

    // Assert
    expect(
      screen.getByText("Todavía no se guardaron métricas para este creador."),
    ).toBeVisible()
    expect(screen.queryByText(/^Posts \(/)).not.toBeInTheDocument()
    expect(screen.queryByText(/^Reels \(/)).not.toBeInTheDocument()
  })

  test("creator_snapshot_detail_dialog_close_button_notifies_parent", async () => {
    // Arrange
    const user = userEvent.setup()
    const onOpenChange = vi.fn()
    renderWithProviders(
      <CreatorSnapshotDetailDialog
        onOpenChange={onOpenChange}
        snapshot={createSnapshot()}
      />,
      { language: "en" },
    )

    // Act
    await user.click(screen.getByRole("button", { name: "Close" }))

    // Assert
    expect(onOpenChange).toHaveBeenCalledWith(false)
  })
})
