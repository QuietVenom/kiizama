import { useMemo, useState } from "react"
import { useForm, useWatch } from "react-hook-form"

import CreatorStrategyBuilder from "@/components/BrandIntelligence/CreatorStrategyBuilder"
import {
  type CreatorFormValues,
  creatorFormDefaultValues,
  creatorTextInputDefaultValues,
} from "@/features/brand-intelligence/form-values"
import { useProfileExistenceValidation } from "@/features/brand-intelligence/use-profile-existence-validation"
import { normalizeUsernameList } from "@/features/brand-intelligence/utils"

const EMPTY_USERNAMES: string[] = []

export function CreatorStrategyTab() {
  const [creatorTextInputValues, setCreatorTextInputValues] = useState(
    creatorTextInputDefaultValues,
  )

  const form = useForm<CreatorFormValues>({
    mode: "onBlur",
    shouldUnregister: false,
    defaultValues: creatorFormDefaultValues,
  })

  const creatorUsernameValue = useWatch({
    control: form.control,
    name: "creator_username",
    defaultValue: creatorFormDefaultValues.creator_username,
  })

  const creatorUsername = useMemo(
    () => normalizeUsernameList([creatorUsernameValue ?? ""])[0] ?? "",
    [creatorUsernameValue],
  )
  const creatorValidationUsernames = useMemo(
    () => (creatorUsername ? [creatorUsername] : EMPTY_USERNAMES),
    [creatorUsername],
  )

  const validation = useProfileExistenceValidation(creatorValidationUsernames)

  return (
    <CreatorStrategyBuilder
      creatorTextInputValues={creatorTextInputValues}
      creatorUsername={creatorUsername}
      creatorValidationUsernames={creatorValidationUsernames}
      form={form}
      onTextInputValuesChange={setCreatorTextInputValues}
      validation={validation}
    />
  )
}

export default CreatorStrategyTab
