import type {
  ReputationCampaignStrategyRequest,
  ReputationCreatorStrategyRequest,
  ReputationSignalsInput,
} from "@/client"

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
