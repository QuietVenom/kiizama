import type { TFunction } from "i18next"

type BrandIntelligenceT = TFunction<"brandIntelligence">

export const BRAND_GOALS_TYPE_OPTIONS = [
  "Trust & Credibility Acceleration",
  "Repositioning",
  "Crisis",
] as const

export const CREATOR_GOAL_TYPE_OPTIONS = [
  "Community Trust",
  "Resilience",
  "Pivot",
] as const

export const AUDIENCE_OPTIONS = [
  "Gen Z",
  "Zillennials",
  "Millennials",
  "Gen X",
  "Boomers",
] as const

export const TIMEFRAME_OPTIONS = ["3 months", "6 months", "12 months"] as const

export const CAMPAIGN_TYPE_OPTIONS = [
  {
    name: "all_nano_seeding_ugc_flood",
    titleKey: "catalogs.campaignTypes.all_nano_seeding_ugc_flood.title",
    descriptionKey:
      "catalogs.campaignTypes.all_nano_seeding_ugc_flood.description",
  },
  {
    name: "all_micro_performance_community_trust",
    titleKey:
      "catalogs.campaignTypes.all_micro_performance_community_trust.title",
    descriptionKey:
      "catalogs.campaignTypes.all_micro_performance_community_trust.description",
  },
  {
    name: "micro_city_blitz",
    titleKey: "catalogs.campaignTypes.micro_city_blitz.title",
    descriptionKey: "catalogs.campaignTypes.micro_city_blitz.description",
  },
  {
    name: "all_mid_tier_reach_eficiente",
    titleKey: "catalogs.campaignTypes.all_mid_tier_reach_eficiente.title",
    descriptionKey:
      "catalogs.campaignTypes.all_mid_tier_reach_eficiente.description",
  },
  {
    name: "macro_plus_micro_swarm_hero_halo",
    titleKey: "catalogs.campaignTypes.macro_plus_micro_swarm_hero_halo.title",
    descriptionKey:
      "catalogs.campaignTypes.macro_plus_micro_swarm_hero_halo.description",
  },
  {
    name: "mega_plus_mid_support",
    titleKey: "catalogs.campaignTypes.mega_plus_mid_support.title",
    descriptionKey: "catalogs.campaignTypes.mega_plus_mid_support.description",
  },
  {
    name: "mid_plus_micro_always_on",
    titleKey: "catalogs.campaignTypes.mid_plus_micro_always_on.title",
    descriptionKey:
      "catalogs.campaignTypes.mid_plus_micro_always_on.description",
  },
  {
    name: "celebrity_plus_community_creators",
    titleKey: "catalogs.campaignTypes.celebrity_plus_community_creators.title",
    descriptionKey:
      "catalogs.campaignTypes.celebrity_plus_community_creators.description",
  },
  {
    name: "vertical_experts_authority",
    titleKey: "catalogs.campaignTypes.vertical_experts_authority.title",
    descriptionKey:
      "catalogs.campaignTypes.vertical_experts_authority.description",
  },
  {
    name: "ugc_creators",
    titleKey: "catalogs.campaignTypes.ugc_creators.title",
    descriptionKey: "catalogs.campaignTypes.ugc_creators.description",
  },
  {
    name: "event_amplification",
    titleKey: "catalogs.campaignTypes.event_amplification.title",
    descriptionKey: "catalogs.campaignTypes.event_amplification.description",
  },
  {
    name: "challenge_trend_wave",
    titleKey: "catalogs.campaignTypes.challenge_trend_wave.title",
    descriptionKey: "catalogs.campaignTypes.challenge_trend_wave.description",
  },
  {
    name: "creator_squad_ambassadors",
    titleKey: "catalogs.campaignTypes.creator_squad_ambassadors.title",
    descriptionKey:
      "catalogs.campaignTypes.creator_squad_ambassadors.description",
  },
  {
    name: "retargeting_booster_paid_whitelisting",
    titleKey:
      "catalogs.campaignTypes.retargeting_booster_paid_whitelisting.title",
    descriptionKey:
      "catalogs.campaignTypes.retargeting_booster_paid_whitelisting.description",
  },
] as const

const BRAND_GOAL_LABEL_KEYS: Record<
  (typeof BRAND_GOALS_TYPE_OPTIONS)[number],
  string
> = {
  "Trust & Credibility Acceleration":
    "catalogs.brandGoals.trustCredibilityAcceleration",
  Repositioning: "catalogs.brandGoals.repositioning",
  Crisis: "catalogs.brandGoals.crisis",
}

const CREATOR_GOAL_LABEL_KEYS: Record<
  (typeof CREATOR_GOAL_TYPE_OPTIONS)[number],
  string
> = {
  "Community Trust": "catalogs.creatorGoals.communityTrust",
  Resilience: "catalogs.creatorGoals.resilience",
  Pivot: "catalogs.creatorGoals.pivot",
}

const AUDIENCE_LABEL_KEYS: Record<(typeof AUDIENCE_OPTIONS)[number], string> = {
  "Gen Z": "catalogs.audiences.genZ",
  Zillennials: "catalogs.audiences.zillennials",
  Millennials: "catalogs.audiences.millennials",
  "Gen X": "catalogs.audiences.genX",
  Boomers: "catalogs.audiences.boomers",
}

const TIMEFRAME_LABEL_KEYS: Record<(typeof TIMEFRAME_OPTIONS)[number], string> =
  {
    "3 months": "catalogs.timeframes.threeMonths",
    "6 months": "catalogs.timeframes.sixMonths",
    "12 months": "catalogs.timeframes.twelveMonths",
  }

export const getBrandGoalTypeLabel = (
  t: BrandIntelligenceT,
  value: (typeof BRAND_GOALS_TYPE_OPTIONS)[number],
) => t(BRAND_GOAL_LABEL_KEYS[value])

export const getCreatorGoalTypeLabel = (
  t: BrandIntelligenceT,
  value: (typeof CREATOR_GOAL_TYPE_OPTIONS)[number],
) => t(CREATOR_GOAL_LABEL_KEYS[value])

export const getAudienceLabel = (
  t: BrandIntelligenceT,
  value: (typeof AUDIENCE_OPTIONS)[number],
) => t(AUDIENCE_LABEL_KEYS[value])

export const getTimeframeLabel = (
  t: BrandIntelligenceT,
  value: (typeof TIMEFRAME_OPTIONS)[number],
) => t(TIMEFRAME_LABEL_KEYS[value])

export const getBrandGoalTypeOptions = (t: BrandIntelligenceT) =>
  BRAND_GOALS_TYPE_OPTIONS.map((value) => ({
    label: getBrandGoalTypeLabel(t, value),
    value,
  }))

export const getCreatorGoalTypeOptions = (t: BrandIntelligenceT) =>
  CREATOR_GOAL_TYPE_OPTIONS.map((value) => ({
    label: getCreatorGoalTypeLabel(t, value),
    value,
  }))

export const getAudienceOptions = (t: BrandIntelligenceT) =>
  AUDIENCE_OPTIONS.map((value) => ({
    label: getAudienceLabel(t, value),
    value,
  }))

export const getTimeframeOptions = (t: BrandIntelligenceT) =>
  TIMEFRAME_OPTIONS.map((value) => ({
    label: getTimeframeLabel(t, value),
    value,
  }))

export const getCampaignTypeContent = (
  t: BrandIntelligenceT,
  name: (typeof CAMPAIGN_TYPE_OPTIONS)[number]["name"],
) => {
  const option = CAMPAIGN_TYPE_OPTIONS.find((entry) => entry.name === name)

  if (!option) return null

  return {
    description: t(option.descriptionKey),
    title: t(option.titleKey),
  }
}

export const getCampaignTypeOptions = (t: BrandIntelligenceT) =>
  CAMPAIGN_TYPE_OPTIONS.map((option) => ({
    label: t(option.titleKey),
    value: option.name,
  }))
