import { screen, waitFor, within } from "@testing-library/react"
import { afterEach, describe, expect, test, vi } from "vitest"

import { BrandIntelligenceService } from "../../../src/client"
import {
  CreatorCostEstimate,
  resolveCreatorCostTier,
} from "../../../src/components/CreatorsSearch/CreatorCostEstimate"
import { formatNumber } from "../../../src/i18n"
import { renderWithProviders } from "../helpers/render"

const tiers = [
  {
    key: "micro",
    label: "Micro (10k-100k)",
    min_followers: 10_000,
    max_followers: 99_999,
    min_mxn: 6_000,
    average_mxn: 10_500,
    max_mxn: 15_000,
    typical_deliverable: "1 post / 1 short video",
    notes: "",
    is_manual: false,
  },
  {
    key: "mega",
    label: "Mega (1M+)",
    min_followers: 1_000_000,
    max_followers: null,
    min_mxn: 150_000,
    average_mxn: 575_000,
    max_mxn: 1_000_000,
    typical_deliverable: "1 post / 1 short video",
    notes: "",
    is_manual: false,
  },
  {
    key: "celebrity",
    label: "Celebrity",
    min_followers: null,
    max_followers: null,
    min_mxn: 250_000,
    average_mxn: 1_375_000,
    max_mxn: 2_500_000,
    typical_deliverable: "1 post/video",
    notes: "",
    is_manual: true,
  },
]

afterEach(() => vi.restoreAllMocks())

describe("creator cost estimate", () => {
  test("creator_cost_estimate_matches_follower_tier_without_manual_celebrity", () => {
    expect(resolveCreatorCostTier(75_000, tiers)?.key).toBe("micro")
    expect(resolveCreatorCostTier(100_000, tiers)).toBeUndefined()
    expect(resolveCreatorCostTier(500, tiers)).toBeUndefined()
  })

  test("creator_cost_estimate_displays_range_average_and_deliverable_notes", async () => {
    vi.spyOn(BrandIntelligenceService, "readCostTiers").mockResolvedValue(tiers)

    renderWithProviders(<CreatorCostEstimate followerCount={75_000} />)

    const estimate = within(
      screen.getByRole("region", { name: "Costo estimado" }),
    )
    await waitFor(() =>
      expect(estimate.getByText("Micro (10k-100k)")).toBeVisible(),
    )
    expect(estimate.getByText("Rango bajo")).toBeVisible()
    expect(estimate.getByText("Promedio")).toBeVisible()
    expect(estimate.getByText("Rango alto")).toBeVisible()
    expect(estimate.getByText(formatNumber(6_000, "es"))).toBeVisible()
    expect(estimate.getByText(formatNumber(10_500, "es"))).toBeVisible()
    expect(estimate.getByText(formatNumber(15_000, "es"))).toBeVisible()
    expect(estimate.getAllByText("MXN")).toHaveLength(3)
    expect(estimate.getByText(/1 post o reel/)).toBeVisible()
    expect(estimate.getByText(/2–4 stories/)).toBeVisible()
    expect(estimate.getByText(/Precio mínimo estimado/)).toBeVisible()
    expect(
      estimate.getByText(/Precio promedio para estimaciones/),
    ).toBeVisible()
    expect(
      estimate.getByText(/Precio máximo estimado para este segmento/),
    ).toBeVisible()
    expect(estimate.queryByText(/1M o más seguidores/)).not.toBeInTheDocument()
    expect(estimate.getByText(/¡Aviso!/)).toBeVisible()
    expect(estimate.getByText(/más de 10M de seguidores/)).toBeVisible()
  })

  test("mega_range_explains_the_one_million_follower_segment", async () => {
    vi.spyOn(BrandIntelligenceService, "readCostTiers").mockResolvedValue(tiers)

    renderWithProviders(<CreatorCostEstimate followerCount={1_500_000} />)

    const estimate = within(
      screen.getByRole("region", { name: "Costo estimado" }),
    )
    await waitFor(() => expect(estimate.getByText("Mega (1M+)")).toBeVisible())
    expect(estimate.getByText(/1M o más seguidores/)).toBeVisible()
  })

  test("creator_cost_estimate_below_nano_does_not_call_catalog", () => {
    const readCostTiers = vi.spyOn(BrandIntelligenceService, "readCostTiers")

    renderWithProviders(<CreatorCostEstimate followerCount={900} />)

    expect(screen.getByText(/Sin estimación automática/)).toBeVisible()
    expect(readCostTiers).not.toHaveBeenCalled()
  })
})
