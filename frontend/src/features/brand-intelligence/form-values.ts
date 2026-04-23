import type {
  ReputationCampaignStrategyRequest,
  ReputationCreatorStrategyRequest,
  ReputationSignalsInput,
} from "@/client"
import { normalizeListValues, normalizeUsernameList } from "./utils"

export type CampaignFormValues = Omit<
  ReputationCampaignStrategyRequest,
  "generate_html" | "generate_pdf"
>

export const campaignFormDefaultValues: CampaignFormValues = {
  audience: [],
  brand_context: "",
  brand_goals_context: "",
  brand_goals_type: "",
  brand_name: "",
  brand_urls: [],
  campaign_type: "",
  profiles_list: [],
  timeframe: "",
}

export type CreatorFormValues = Omit<
  ReputationCreatorStrategyRequest,
  "generate_html" | "generate_pdf"
> & {
  reputation_signals: ReputationSignalsInput
}

export const creatorFormDefaultValues: CreatorFormValues = {
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
}

export type CreatorTextInputValues = {
  collaborators: string
  concerns: string
  creatorUsername: string
  incidents: string
  primaryPlatforms: string
  strengths: string
  weaknesses: string
}

export const creatorTextInputDefaultValues: CreatorTextInputValues = {
  collaborators: "",
  concerns: "",
  creatorUsername: "",
  incidents: "",
  primaryPlatforms: "",
  strengths: "",
  weaknesses: "",
}

type ReportOutputOptions = {
  generateHtml?: boolean
  generatePdf?: boolean
}

type CampaignPayloadOptions = ReportOutputOptions & {
  profilesList?: string[]
}

export const buildCampaignStrategyPayload = (
  values: CampaignFormValues,
  {
    generateHtml = false,
    generatePdf = true,
    profilesList,
  }: CampaignPayloadOptions = {},
): ReputationCampaignStrategyRequest => ({
  ...values,
  audience: normalizeListValues(values.audience ?? []),
  brand_context: values.brand_context.trim(),
  brand_goals_context: values.brand_goals_context.trim(),
  brand_name: values.brand_name.trim(),
  brand_urls: normalizeListValues(values.brand_urls ?? []),
  campaign_type: values.campaign_type,
  generate_html: generateHtml,
  generate_pdf: generatePdf,
  profiles_list: profilesList ?? normalizeUsernameList(values.profiles_list),
  timeframe: values.timeframe,
})

const normalizeReputationSignals = (
  reputationSignals: ReputationSignalsInput | null | undefined,
) => ({
  concerns: normalizeListValues(reputationSignals?.concerns ?? []),
  incidents: normalizeListValues(reputationSignals?.incidents ?? []),
  strengths: normalizeListValues(reputationSignals?.strengths ?? []),
  weaknesses: normalizeListValues(reputationSignals?.weaknesses ?? []),
})

export const buildCreatorStrategyPayload = (
  values: CreatorFormValues,
  { generateHtml = false, generatePdf = true }: ReportOutputOptions = {},
): ReputationCreatorStrategyRequest => {
  const cleanedSignals = normalizeReputationSignals(values.reputation_signals)
  const hasSignals = Object.values(cleanedSignals).some(
    (entries) => entries.length > 0,
  )
  const collaborators = normalizeListValues(values.collaborators_list ?? [])

  return {
    ...values,
    audience: normalizeListValues(values.audience ?? []),
    collaborators_list: collaborators.length > 0 ? collaborators : undefined,
    creator_context: values.creator_context.trim(),
    creator_urls: normalizeListValues(values.creator_urls ?? []),
    creator_username: normalizeUsernameList([values.creator_username])[0] ?? "",
    generate_html: generateHtml,
    generate_pdf: generatePdf,
    goal_context: values.goal_context.trim(),
    goal_type: values.goal_type,
    primary_platforms: normalizeListValues(values.primary_platforms ?? []),
    reputation_signals: hasSignals ? cleanedSignals : undefined,
    timeframe: values.timeframe,
  }
}
