import { useMemo } from "react"
import { useForm, useWatch } from "react-hook-form"

import CampaignStrategyBuilder from "@/components/BrandIntelligence/CampaignStrategyBuilder"
import {
  type CampaignFormValues,
  campaignFormDefaultValues,
} from "@/features/brand-intelligence/form-values"
import { useProfileExistenceValidation } from "@/features/brand-intelligence/use-profile-existence-validation"
import { normalizeUsernameList } from "@/features/brand-intelligence/utils"

export function CampaignStrategyTab() {
  const form = useForm<CampaignFormValues>({
    mode: "onBlur",
    shouldUnregister: false,
    defaultValues: campaignFormDefaultValues,
  })

  const campaignProfilesValue = useWatch({
    control: form.control,
    name: "profiles_list",
    defaultValue: campaignFormDefaultValues.profiles_list,
  })

  const normalizedProfiles = useMemo(
    () => normalizeUsernameList(campaignProfilesValue ?? []),
    [campaignProfilesValue],
  )

  const validation = useProfileExistenceValidation(normalizedProfiles)

  return (
    <CampaignStrategyBuilder
      form={form}
      normalizedProfiles={normalizedProfiles}
      validation={validation}
    />
  )
}

export default CampaignStrategyTab
