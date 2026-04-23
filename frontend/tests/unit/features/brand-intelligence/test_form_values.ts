import { describe, expect, test } from "vitest"

import {
  buildCampaignStrategyPayload,
  buildCreatorStrategyPayload,
  type CampaignFormValues,
  type CreatorFormValues,
  campaignFormDefaultValues,
  creatorFormDefaultValues,
  creatorTextInputDefaultValues,
} from "../../../../src/features/brand-intelligence/form-values"

const createCampaignValues = (
  overrides: Partial<CampaignFormValues> = {},
): CampaignFormValues => ({
  ...campaignFormDefaultValues,
  audience: [" Gen Z ", "Gen Z", "Millennials"],
  brand_context: "  Brand context  ",
  brand_goals_context: "  Goal context  ",
  brand_goals_type: "Crisis",
  brand_name: "  Kiizama  ",
  brand_urls: [" https://kiizama.com ", "", "https://kiizama.com"],
  campaign_type: "all_nano_seeding_ugc_flood",
  profiles_list: [" @Creator.One ", "creator.one", "", "@Second_Creator"],
  timeframe: "3 months",
  ...overrides,
})

const createCreatorValues = (
  overrides: Partial<CreatorFormValues> = {},
): CreatorFormValues => ({
  ...creatorFormDefaultValues,
  audience: ["Gen Z", " Gen Z ", "Millennials"],
  collaborators_list: [" Brand One ", "", "Brand One", "@BrandTwo"],
  creator_context: "  Creator context  ",
  creator_urls: [" https://creator.test ", "", "https://creator.test"],
  creator_username: " @Creator.One ",
  goal_context: "  Goal context  ",
  goal_type: "Community Trust",
  primary_platforms: [" Instagram ", "TikTok", "Instagram"],
  reputation_signals: {
    concerns: [" Fatigue ", "", "Fatigue"],
    incidents: [],
    strengths: [" Trust ", "Trust"],
    weaknesses: [""],
  },
  timeframe: "6 months",
  ...overrides,
})

describe("brand intelligence form values", () => {
  test("brand_intelligence_defaults_expose_empty_campaign_creator_and_text_state", () => {
    // Arrange / Act / Assert
    expect(campaignFormDefaultValues).toEqual({
      audience: [],
      brand_context: "",
      brand_goals_context: "",
      brand_goals_type: "",
      brand_name: "",
      brand_urls: [],
      campaign_type: "",
      profiles_list: [],
      timeframe: "",
    })
    expect(creatorFormDefaultValues).toEqual({
      audience: [],
      collaborators_list: [],
      creator_context: "",
      creator_urls: [],
      creator_username: "",
      goal_context: "",
      goal_type: "",
      primary_platforms: [],
      reputation_signals: {
        concerns: [],
        incidents: [],
        strengths: [],
        weaknesses: [],
      },
      timeframe: "",
    })
    expect(creatorTextInputDefaultValues).toEqual({
      collaborators: "",
      concerns: "",
      creatorUsername: "",
      incidents: "",
      primaryPlatforms: "",
      strengths: "",
      weaknesses: "",
    })
  })

  test("campaign_payload_builder_normalizes_values_and_output_flags", () => {
    // Arrange
    const values = createCampaignValues()

    // Act
    const payload = buildCampaignStrategyPayload(values, {
      generateHtml: true,
      generatePdf: false,
    })

    // Assert
    expect(payload).toMatchObject({
      audience: ["Gen Z", "Millennials"],
      brand_context: "Brand context",
      brand_goals_context: "Goal context",
      brand_goals_type: "Crisis",
      brand_name: "Kiizama",
      brand_urls: ["https://kiizama.com"],
      campaign_type: "all_nano_seeding_ugc_flood",
      generate_html: true,
      generate_pdf: false,
      profiles_list: ["creator.one", "second_creator"],
      timeframe: "3 months",
    })
  })

  test("campaign_payload_builder_uses_explicit_profiles_for_crisis_without_creators", () => {
    // Arrange
    const values = createCampaignValues()

    // Act
    const payload = buildCampaignStrategyPayload(values, { profilesList: [] })

    // Assert
    expect(payload.profiles_list).toEqual([])
    expect(payload.generate_html).toBe(false)
    expect(payload.generate_pdf).toBe(true)
  })

  test("creator_payload_builder_normalizes_username_lists_signals_and_optional_fields", () => {
    // Arrange
    const values = createCreatorValues()

    // Act
    const payload = buildCreatorStrategyPayload(values)

    // Assert
    expect(payload).toMatchObject({
      audience: ["Gen Z", "Millennials"],
      collaborators_list: ["Brand One", "@BrandTwo"],
      creator_context: "Creator context",
      creator_urls: ["https://creator.test"],
      creator_username: "creator.one",
      generate_html: false,
      generate_pdf: true,
      goal_context: "Goal context",
      goal_type: "Community Trust",
      primary_platforms: ["Instagram", "TikTok"],
      reputation_signals: {
        concerns: ["Fatigue"],
        incidents: [],
        strengths: ["Trust"],
        weaknesses: [],
      },
      timeframe: "6 months",
    })
  })

  test("creator_payload_builder_omits_empty_collaborators_and_reputation_signals", () => {
    // Arrange
    const values = createCreatorValues({
      collaborators_list: ["", "  "],
      reputation_signals: {
        concerns: [""],
        incidents: [],
        strengths: [],
        weaknesses: [],
      },
    })

    // Act
    const payload = buildCreatorStrategyPayload(values, {
      generateHtml: true,
      generatePdf: false,
    })

    // Assert
    expect(payload.collaborators_list).toBeUndefined()
    expect(payload.reputation_signals).toBeUndefined()
    expect(payload.generate_html).toBe(true)
    expect(payload.generate_pdf).toBe(false)
  })
})
