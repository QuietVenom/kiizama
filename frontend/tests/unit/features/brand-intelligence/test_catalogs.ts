import { describe, expect, test } from "vitest"

import {
  AUDIENCE_OPTIONS,
  BRAND_GOALS_TYPE_OPTIONS,
  CAMPAIGN_TYPE_OPTIONS,
  CREATOR_GOAL_TYPE_OPTIONS,
  TIMEFRAME_OPTIONS,
} from "../../../../src/features/brand-intelligence/catalogs"

describe("brand intelligence catalogs", () => {
  test("catalogs_core_options_are_non_empty_and_stable_for_ui_forms", () => {
    // Arrange / Act / Assert
    expect(BRAND_GOALS_TYPE_OPTIONS).toEqual([
      "Trust & Credibility Acceleration",
      "Repositioning",
      "Crisis",
    ])
    expect(CREATOR_GOAL_TYPE_OPTIONS).toEqual([
      "Community Trust",
      "Resilience",
      "Pivot",
    ])
    expect(AUDIENCE_OPTIONS).toContain("Gen Z")
    expect(AUDIENCE_OPTIONS).toContain("Millennials")
    expect(TIMEFRAME_OPTIONS).toEqual(["3 months", "6 months", "12 months"])
  })

  test("campaign_catalog_entries_have_required_contract_fields", () => {
    // Arrange / Act
    const invalidEntries = CAMPAIGN_TYPE_OPTIONS.filter(
      (option) => !option.name || !option.title || !option.value,
    )

    // Assert
    expect(CAMPAIGN_TYPE_OPTIONS.length).toBeGreaterThan(0)
    expect(invalidEntries).toEqual([])
  })

  test("campaign_catalog_names_are_unique_and_include_critical_strategies", () => {
    // Arrange
    const names = CAMPAIGN_TYPE_OPTIONS.map((option) => option.name)

    // Act / Assert
    expect(new Set(names).size).toBe(names.length)
    expect(names).toEqual(
      expect.arrayContaining([
        "all_nano_seeding_ugc_flood",
        "all_micro_performance_community_trust",
        "creator_squad_ambassadors",
        "ugc_creators",
      ]),
    )
  })

  test("campaign_catalog_labels_preserve_user_facing_copy", () => {
    // Arrange
    const nano = CAMPAIGN_TYPE_OPTIONS.find(
      (option) => option.name === "all_nano_seeding_ugc_flood",
    )
    const ambassadors = CAMPAIGN_TYPE_OPTIONS.find(
      (option) => option.name === "creator_squad_ambassadors",
    )

    // Act / Assert
    expect(nano?.title).toContain("Nano")
    expect(nano?.value).toContain("UGC")
    expect(ambassadors?.title).toContain("embajadores")
  })
})
