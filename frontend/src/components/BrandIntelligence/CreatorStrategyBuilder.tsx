import {
  Badge,
  Box,
  Flex,
  Grid,
  NativeSelect,
  Text,
  Textarea,
} from "@chakra-ui/react"
import { useMutation } from "@tanstack/react-query"
import { type Dispatch, type SetStateAction, useMemo, useState } from "react"
import {
  type Control,
  Controller,
  type FieldPath,
  type FieldValues,
  type UseFormReturn,
  useWatch,
} from "react-hook-form"
import { FiAlertCircle, FiFileText, FiSearch } from "react-icons/fi"

import { Button } from "@/components/ui/button"
import { Field } from "@/components/ui/field"
import { TagsInputField } from "@/components/ui/tags-input-field"
import {
  BRAND_INTELLIGENCE_CREATOR_ENDPOINT,
  generateBrandIntelligenceReport,
} from "@/features/brand-intelligence/api"
import {
  AUDIENCE_OPTIONS,
  CREATOR_GOAL_TYPE_OPTIONS,
  TIMEFRAME_OPTIONS,
} from "@/features/brand-intelligence/catalogs"
import {
  BRAND_INTELLIGENCE_LIMITS,
  CREATOR_FIELD_HELP,
  REPUTATION_SIGNAL_FIELD_HELP,
} from "@/features/brand-intelligence/form-config"
import type {
  CreatorFormValues,
  CreatorTextInputValues,
} from "@/features/brand-intelligence/form-values"
import type { useProfileExistenceValidation } from "@/features/brand-intelligence/use-profile-existence-validation"
import {
  isValidHttpUrl,
  normalizeListValues,
  normalizeUsernameList,
} from "@/features/brand-intelligence/utils"
import useCustomToast from "@/hooks/useCustomToast"
import { extractApiErrorMessage } from "@/lib/api-errors"
import { isValidInstagramUsername } from "@/lib/instagram-usernames"
import { saveLocalReport } from "@/lib/local-reports"
import { downloadBlob } from "@/lib/report-files"
import FieldHelperWithCounter from "./FieldHelperWithCounter"
import FieldLabelWithInfo from "./FieldLabelWithInfo"
import MultiSelectOptionGroup from "./MultiSelectOptionGroup"
import ProfileValidationPanel from "./ProfileValidationPanel"
import StrategySection from "./StrategySection"
import StrategySummaryCard from "./StrategySummaryCard"

type CreatorStrategyBuilderProps = {
  creatorTextInputValues: CreatorTextInputValues
  creatorUsername: string
  creatorValidationUsernames: string[]
  form: UseFormReturn<CreatorFormValues>
  onTextInputValuesChange: Dispatch<SetStateAction<CreatorTextInputValues>>
  validation: ReturnType<typeof useProfileExistenceValidation>
}

const inputStyles = {
  bg: "ui.panel",
  borderColor: "ui.sidebarBorder",
  rounded: "2xl",
} as const

const getValidationTone = ({
  expired,
  invalid,
  missing,
}: {
  expired: boolean
  invalid: boolean
  missing: boolean
}) => {
  if (invalid || missing) {
    return {
      background: "ui.dangerSoft",
      borderColor: "ui.danger",
      color: "ui.dangerText",
      closeHoverBg: "rgba(220, 38, 38, 0.12)",
    }
  }

  if (expired) {
    return {
      background: "ui.warningSoft",
      borderColor: "ui.warning",
      color: "ui.warningText",
      closeHoverBg: "rgba(217, 119, 6, 0.12)",
    }
  }

  return {
    background: "ui.brandSoft",
    borderColor: "ui.brandBorderSoft",
    color: "ui.brandText",
    closeHoverBg: "rgba(249, 115, 22, 0.10)",
  }
}

const getUrlPalette = (invalidUrls: ReadonlySet<string>, value: string) => {
  if (invalidUrls.has(value)) {
    return {
      background: "ui.dangerSoft",
      borderColor: "ui.danger",
      color: "ui.dangerText",
      closeHoverBg: "rgba(220, 38, 38, 0.12)",
    }
  }

  return {
    background: "ui.brandSoft",
    borderColor: "ui.brandBorderSoft",
    color: "ui.brandText",
    closeHoverBg: "rgba(249, 115, 22, 0.10)",
  }
}

const buildSignalFieldRules = (fieldLabel: string) => ({
  validate: (value: string[] | undefined) => {
    if (
      (value ?? []).some(
        (entry) =>
          entry.length > BRAND_INTELLIGENCE_LIMITS.reputationSignalCharacters,
      )
    ) {
      return `${fieldLabel} entries must use 30 characters or less.`
    }

    return true
  },
})

const normalizeTextareaListValues = (value: string) =>
  normalizeListValues(value.split(/\r?\n/))

const formatTextareaListValues = (value: string[] | null | undefined) =>
  (value ?? []).join("\n")

const getTextareaLineMaxLength = (value: string) =>
  value.split(/\r?\n/).reduce((max, line) => Math.max(max, line.length), 0)

const trimTextareaLineLength = (value: string, limit: number) =>
  value
    .split(/\r?\n/)
    .map((line) => line.slice(0, limit))
    .join("\n")

type CharacterCountHelperProps<TFieldValues extends FieldValues> = {
  control: Control<TFieldValues>
  limit: number
  name: FieldPath<TFieldValues>
}

const CharacterCountHelper = <TFieldValues extends FieldValues>({
  control,
  limit,
  name,
}: CharacterCountHelperProps<TFieldValues>) => {
  const value = useWatch({ control, name })

  return <FieldHelperWithCounter count={(value ?? "").length} limit={limit} />
}

const CreatorStrategySummary = ({
  control,
  creatorUsername,
  expiredUsernames,
}: {
  control: Control<CreatorFormValues>
  creatorUsername: string
  expiredUsernames: string[]
}) => {
  const [
    audience,
    collaboratorsList,
    creatorContext,
    creatorUrls,
    goalContext,
    goalType,
    primaryPlatforms,
    strengths,
    weaknesses,
    incidents,
    concerns,
    timeframe,
  ] = useWatch({
    control,
    name: [
      "audience",
      "collaborators_list",
      "creator_context",
      "creator_urls",
      "goal_context",
      "goal_type",
      "primary_platforms",
      "reputation_signals.strengths",
      "reputation_signals.weaknesses",
      "reputation_signals.incidents",
      "reputation_signals.concerns",
      "timeframe",
    ],
  })

  const normalizedCreatorUrls = useMemo(
    () => normalizeListValues(creatorUrls ?? []),
    [creatorUrls],
  )
  const normalizedPlatforms = useMemo(
    () => normalizeListValues(primaryPlatforms ?? []),
    [primaryPlatforms],
  )
  const normalizedCollaborators = useMemo(
    () => normalizeListValues(collaboratorsList ?? []),
    [collaboratorsList],
  )
  const normalizedSignals = useMemo(
    () => ({
      concerns: normalizeListValues(concerns ?? []),
      incidents: normalizeListValues(incidents ?? []),
      strengths: normalizeListValues(strengths ?? []),
      weaknesses: normalizeListValues(weaknesses ?? []),
    }),
    [concerns, incidents, strengths, weaknesses],
  )

  const summarySections = [
    {
      title: "Profile gate",
      items: [
        {
          label: "Creator username",
          value: creatorUsername ? [`@${creatorUsername}`] : [],
        },
        { label: "Expired profiles", value: expiredUsernames },
      ],
    },
    {
      title: "Creator brief",
      items: [
        { label: "Creator context", value: creatorContext },
        { label: "Creator URLs", value: normalizedCreatorUrls },
        { label: "Goal type", value: goalType },
        { label: "Goal context", value: goalContext },
        { label: "Audience", value: audience ?? [] },
        { label: "Timeframe", value: timeframe },
      ],
    },
    {
      title: "Strategy inputs",
      items: [
        { label: "Primary platforms", value: normalizedPlatforms },
        { label: "Collaborators", value: normalizedCollaborators },
        { label: "Strengths", value: normalizedSignals.strengths },
        { label: "Weaknesses", value: normalizedSignals.weaknesses },
        { label: "Incidents", value: normalizedSignals.incidents },
        { label: "Concerns", value: normalizedSignals.concerns },
      ],
    },
  ]

  return (
    <StrategySummaryCard title="Creator Strategy" sections={summarySections} />
  )
}

const CreatorSubmitPanel = ({
  control,
  creatorUsername,
  invalidCreatorUsername,
  isValidationPending,
  isValidationStale,
  missingUsernames,
  orderedProfilesCount,
  reportIsPending,
}: {
  control: Control<CreatorFormValues>
  creatorUsername: string
  invalidCreatorUsername: boolean
  isValidationPending: boolean
  isValidationStale: boolean
  missingUsernames: string[]
  orderedProfilesCount: number
  reportIsPending: boolean
}) => {
  const [
    audience,
    creatorContext,
    creatorUrls,
    goalContext,
    goalType,
    primaryPlatforms,
    timeframe,
  ] = useWatch({
    control,
    name: [
      "audience",
      "creator_context",
      "creator_urls",
      "goal_context",
      "goal_type",
      "primary_platforms",
      "timeframe",
    ],
  })

  const normalizedCreatorUrls = useMemo(
    () => normalizeListValues(creatorUrls ?? []),
    [creatorUrls],
  )
  const normalizedPlatforms = useMemo(
    () => normalizeListValues(primaryPlatforms ?? []),
    [primaryPlatforms],
  )
  const hasInvalidCreatorUrls = normalizedCreatorUrls.some(
    (value) => !isValidHttpUrl(value),
  )
  const hasRequiredFields =
    Boolean(creatorUsername) &&
    Boolean(creatorContext) &&
    Boolean(goalContext) &&
    Boolean(goalType) &&
    Boolean(timeframe) &&
    (audience?.length ?? 0) > 0 &&
    normalizedPlatforms.length > 0

  const submitDisabledReason = !creatorUsername
    ? "Add the creator username to unlock the workflow."
    : invalidCreatorUsername
      ? "Fix the creator username before continuing."
      : hasInvalidCreatorUrls
        ? "Use valid http or https URLs."
        : !hasRequiredFields
          ? "Complete the required fields to enable report generation."
          : isValidationPending
            ? "Profile validation is still running."
            : isValidationStale || orderedProfilesCount === 0
              ? "Validate the creator profile before generating the report."
              : missingUsernames.length > 0
                ? "consulte los perfiles en Mining y vuelva a intentar"
                : null

  return (
    <Box
      layerStyle="dashboardCard"
      px={{ base: 5, md: 6 }}
      py={{ base: 5, md: 6 }}
    >
      <Flex
        alignItems={{ base: "flex-start", lg: "center" }}
        justifyContent="space-between"
        gap={4}
        direction={{ base: "column", lg: "row" }}
      >
        <Box maxW="58ch">
          <Text fontSize="lg" fontWeight="black">
            Generate creator strategy PDF
          </Text>
          <Text mt={2} color="ui.secondaryText">
            The downloaded PDF is also saved into local storage for the
            dashboard.
          </Text>
          {submitDisabledReason ? (
            <Text mt={3} color="ui.mutedText" fontSize="sm">
              {submitDisabledReason}
            </Text>
          ) : null}
        </Box>

        <Button
          type="submit"
          layerStyle="brandGradientButton"
          loading={reportIsPending}
          disabled={Boolean(submitDisabledReason)}
          alignSelf={{ base: "stretch", lg: "center" }}
        >
          <FiFileText />
          Generate PDF report
        </Button>
      </Flex>
    </Box>
  )
}

const CreatorStrategyBuilder = ({
  creatorTextInputValues,
  creatorUsername,
  creatorValidationUsernames,
  form,
  onTextInputValuesChange,
  validation,
}: CreatorStrategyBuilderProps) => {
  const { showErrorToast, showSuccessToast } = useCustomToast()
  const [submitError, setSubmitError] = useState<string | null>(null)
  const [submitSuccess, setSubmitSuccess] = useState<string | null>(null)
  const setTextInputValues = onTextInputValuesChange

  const {
    control,
    formState: { errors },
    handleSubmit,
    register,
    setValue,
    trigger,
  } = form

  const invalidCreatorUsername =
    creatorUsername.length > 0 && !isValidInstagramUsername(creatorUsername)

  const {
    expiredUsernames,
    isValidationPending,
    isValidationStale,
    missingUsernames,
    orderedProfiles,
    validateProfiles,
    validationError,
  } = validation

  const isWorkflowUnlocked = Boolean(creatorUsername)
  const canRunValidation =
    Boolean(creatorUsername) && !invalidCreatorUsername && !isValidationPending

  const handleValidateProfiles = async () => {
    setSubmitError(null)
    setSubmitSuccess(null)
    setValue("creator_username", creatorUsername, {
      shouldDirty: true,
      shouldValidate: true,
    })

    const isFieldValid = await trigger("creator_username")
    if (!isFieldValid || !creatorUsername) return

    await validateProfiles(creatorValidationUsernames)
  }

  const reportMutation = useMutation({
    mutationFn: async (values: CreatorFormValues) => {
      const normalizedUsername =
        normalizeUsernameList([values.creator_username])[0] ?? ""
      const validationResult = await validateProfiles([normalizedUsername])
      const missingProfiles = (validationResult?.profiles ?? [])
        .filter((profile) => !profile.exists)
        .map((profile) => profile.username)

      if (missingProfiles.length > 0) {
        throw new Error("consulte los perfiles en Mining y vuelva a intentar")
      }

      const cleanedSignals = {
        concerns: normalizeListValues(
          values.reputation_signals?.concerns ?? [],
        ),
        incidents: normalizeListValues(
          values.reputation_signals?.incidents ?? [],
        ),
        strengths: normalizeListValues(
          values.reputation_signals?.strengths ?? [],
        ),
        weaknesses: normalizeListValues(
          values.reputation_signals?.weaknesses ?? [],
        ),
      }

      const hasSignals = Object.values(cleanedSignals).some(
        (entries) => entries.length > 0,
      )

      return generateBrandIntelligenceReport({
        endpointPath: BRAND_INTELLIGENCE_CREATOR_ENDPOINT,
        fallbackFilename: "reputation_creator_strategy.pdf",
        payload: {
          ...values,
          audience: values.audience,
          collaborators_list:
            normalizeListValues(values.collaborators_list ?? []).length > 0
              ? normalizeListValues(values.collaborators_list ?? [])
              : undefined,
          creator_context: values.creator_context.trim(),
          creator_urls: normalizeListValues(values.creator_urls ?? []),
          creator_username: normalizedUsername,
          generate_html: false,
          generate_pdf: true,
          goal_context: values.goal_context.trim(),
          goal_type: values.goal_type,
          primary_platforms: normalizeListValues(
            values.primary_platforms ?? [],
          ),
          reputation_signals: hasSignals ? cleanedSignals : undefined,
          timeframe: values.timeframe,
        },
      })
    },
    onMutate: () => {
      setSubmitError(null)
      setSubmitSuccess(null)
    },
    onSuccess: async ({ blob, filename }) => {
      downloadBlob(blob, filename)
      setSubmitSuccess(`Report ready: ${filename}`)

      try {
        await saveLocalReport({
          blob,
          filename,
          reportType: "reputation-creator-strategy",
          source: "brand-intelligence",
        })
        showSuccessToast("Creator strategy PDF downloaded and saved locally.")
      } catch {
        showErrorToast(
          "Creator strategy PDF downloaded, but it could not be saved locally.",
        )
      }
    },
    onError: (error) => {
      setSubmitError(
        extractApiErrorMessage(error, "Unable to generate the report."),
      )
    },
  })

  const onSubmit = (values: CreatorFormValues) => {
    reportMutation.mutate(values)
  }

  const renderFieldInfo = (label: string, description: string) => (
    <FieldLabelWithInfo label={label} description={description} />
  )

  return (
    <Box
      as="form"
      onSubmit={handleSubmit(onSubmit)}
      display="grid"
      gridTemplateColumns={{ base: "1fr", xl: "minmax(0, 1.65fr) 360px" }}
      gap={6}
    >
      <Flex direction="column" gap={6} minW={0}>
        <StrategySection
          eyebrow="Step 1"
          title="Add the creator username"
          description="The creator username is the first required input. It unlocks the rest of the workflow and must be validated before report generation."
        >
          <Controller
            control={control}
            name="creator_username"
            rules={{
              validate: (value) => {
                const normalizedValue = normalizeUsernameList([value])[0] ?? ""

                if (!normalizedValue) {
                  return "Add the creator username."
                }

                if (!isValidInstagramUsername(normalizedValue)) {
                  return "Use lowercase letters, numbers, periods or underscores, up to 30 characters."
                }

                return true
              },
            }}
            render={({ field, fieldState }) => (
              <Field
                required
                invalid={!!fieldState.error}
                errorText={fieldState.error?.message}
                label="Creator username"
                labelEndElement={renderFieldInfo(
                  "Creator username",
                  CREATOR_FIELD_HELP.creator_username,
                )}
                helperText={
                  <FieldHelperWithCounter
                    count={
                      (
                        creatorTextInputValues.creatorUsername ||
                        creatorUsername
                      ).length
                    }
                    limit={30}
                  />
                }
              >
                <TagsInputField
                  getTagPalette={(value) =>
                    getValidationTone({
                      expired: expiredUsernames.includes(value),
                      invalid: invalidCreatorUsername,
                      missing: missingUsernames.includes(value),
                    })
                  }
                  invalid={!!fieldState.error}
                  inputMaxLength={30}
                  inputValue={creatorTextInputValues.creatorUsername}
                  max={1}
                  onInputValueChange={(value) =>
                    setTextInputValues((prev) => ({
                      ...prev,
                      creatorUsername: value,
                    }))
                  }
                  onValueChange={(nextValue) =>
                    field.onChange(normalizeUsernameList(nextValue)[0] ?? "")
                  }
                  placeholder="creator_one"
                  renderTagLabel={(value) => `@${value}`}
                  value={creatorValidationUsernames}
                />
              </Field>
            )}
          />

          <Flex
            mt={4}
            alignItems="center"
            justifyContent="space-between"
            gap={3}
            wrap="wrap"
          >
            <Badge
              rounded="full"
              borderWidth="1px"
              borderColor="ui.border"
              bg="ui.surfaceSoft"
              color="ui.secondaryText"
              px={3}
              py={1.5}
            >
              {creatorUsername ? "1 / 1 username" : "0 / 1 username"}
            </Badge>

            <Button
              type="button"
              variant="outline"
              onClick={handleValidateProfiles}
              disabled={!canRunValidation}
              loading={isValidationPending}
            >
              <FiSearch />
              Validate profile
            </Button>
          </Flex>

          <Box mt={4}>
            <ProfileValidationPanel
              error={validationError}
              isLoading={isValidationPending}
              isStale={isValidationStale}
              profiles={orderedProfiles}
              usernames={creatorValidationUsernames}
            />
          </Box>
        </StrategySection>

        <StrategySection
          eyebrow="Step 2"
          title="Creator and reputation brief"
          description="Capture the creator context, reputation goal, and supporting URLs that should shape the strategy."
        >
          <Grid templateColumns={{ base: "1fr", lg: "repeat(2, 1fr)" }} gap={4}>
            <Field
              required
              invalid={!!errors.goal_type}
              errorText={errors.goal_type?.message}
              label="Goal type"
              labelEndElement={renderFieldInfo(
                "Goal type",
                CREATOR_FIELD_HELP.goal_type,
              )}
            >
              <NativeSelect.Root disabled={!isWorkflowUnlocked}>
                <NativeSelect.Field
                  {...register("goal_type", {
                    required: "Select the primary reputation goal.",
                  })}
                  {...inputStyles}
                >
                  <option value="">Select a goal</option>
                  {CREATOR_GOAL_TYPE_OPTIONS.map((option) => (
                    <option key={option} value={option}>
                      {option}
                    </option>
                  ))}
                </NativeSelect.Field>
                <NativeSelect.Indicator />
              </NativeSelect.Root>
            </Field>

            <Field
              required
              invalid={!!errors.timeframe}
              errorText={errors.timeframe?.message}
              label="Timeframe"
              labelEndElement={renderFieldInfo(
                "Timeframe",
                CREATOR_FIELD_HELP.timeframe,
              )}
            >
              <NativeSelect.Root disabled={!isWorkflowUnlocked}>
                <NativeSelect.Field
                  {...register("timeframe", {
                    required: "Select the timeframe.",
                  })}
                  {...inputStyles}
                >
                  <option value="">Select a timeframe</option>
                  {TIMEFRAME_OPTIONS.map((option) => (
                    <option key={option} value={option}>
                      {option}
                    </option>
                  ))}
                </NativeSelect.Field>
                <NativeSelect.Indicator />
              </NativeSelect.Root>
            </Field>
          </Grid>

          <Grid
            mt={4}
            templateColumns={{ base: "1fr", lg: "repeat(2, 1fr)" }}
            gap={4}
          >
            <Field
              required
              invalid={!!errors.creator_context}
              errorText={errors.creator_context?.message}
              label="Creator context"
              labelEndElement={renderFieldInfo(
                "Creator context",
                CREATOR_FIELD_HELP.creator_context,
              )}
              helperText={
                <CharacterCountHelper
                  control={control}
                  name="creator_context"
                  limit={500}
                />
              }
            >
              <Textarea
                {...register("creator_context", {
                  required: "Creator context is required.",
                  maxLength: {
                    value: 500,
                    message: "Use 500 characters or less.",
                  },
                })}
                {...inputStyles}
                disabled={!isWorkflowUnlocked}
                maxLength={500}
                minH="132px"
                placeholder="Describe the creator's current narrative, positioning, and public perception."
              />
            </Field>

            <Field
              required
              invalid={!!errors.goal_context}
              errorText={errors.goal_context?.message}
              label="Goal context"
              labelEndElement={renderFieldInfo(
                "Goal context",
                CREATOR_FIELD_HELP.goal_context,
              )}
              helperText={
                <CharacterCountHelper
                  control={control}
                  name="goal_context"
                  limit={500}
                />
              }
            >
              <Textarea
                {...register("goal_context", {
                  required: "Goal context is required.",
                  maxLength: {
                    value: 500,
                    message: "Use 500 characters or less.",
                  },
                })}
                {...inputStyles}
                disabled={!isWorkflowUnlocked}
                maxLength={500}
                minH="132px"
                placeholder="Explain what should change in the creator's reputation over the selected timeframe."
              />
            </Field>
          </Grid>

          <Box mt={4}>
            <Controller
              control={control}
              name="creator_urls"
              rules={{
                validate: (value) => {
                  if (
                    (value ?? []).length > BRAND_INTELLIGENCE_LIMITS.creatorUrls
                  ) {
                    return "Add up to 3 creator URLs."
                  }

                  if ((value ?? []).some((url) => !isValidHttpUrl(url))) {
                    return "Use valid http or https URLs."
                  }

                  return true
                },
              }}
              render={({ field, fieldState }) => {
                const normalizedCreatorUrls = normalizeListValues(
                  field.value ?? [],
                )
                const invalidCreatorUrlSet = new Set(
                  normalizedCreatorUrls.filter(
                    (value) => !isValidHttpUrl(value),
                  ),
                )

                return (
                  <Field
                    invalid={!!fieldState.error}
                    errorText={fieldState.error?.message}
                    label="Creator URLs"
                    labelEndElement={renderFieldInfo(
                      "Creator URLs",
                      CREATOR_FIELD_HELP.creator_urls,
                    )}
                    helperText={
                      fieldState.error
                        ? undefined
                        : "Optional. Add up to 3 relevant URLs for the creator."
                    }
                  >
                    <TagsInputField
                      disabled={!isWorkflowUnlocked}
                      getTagPalette={(value) =>
                        getUrlPalette(invalidCreatorUrlSet, value)
                      }
                      invalid={!!fieldState.error}
                      max={BRAND_INTELLIGENCE_LIMITS.creatorUrls}
                      onValueChange={(nextValue) =>
                        field.onChange(normalizeListValues(nextValue))
                      }
                      placeholder="https://instagram.com/creator, https://youtube.com/@creator"
                      value={field.value ?? []}
                    />
                  </Field>
                )
              }}
            />
          </Box>
        </StrategySection>

        <StrategySection
          eyebrow="Step 3"
          title="Strategy inputs"
          description="Add the audience, key platforms, reputation signals, and collaborators that should inform the creator strategy report."
        >
          <Controller
            control={control}
            name="audience"
            rules={{
              validate: (value) => {
                if (!value || value.length === 0) {
                  return "Select at least 1 audience."
                }

                if (value.length > BRAND_INTELLIGENCE_LIMITS.audience) {
                  return "Select up to 5 audiences."
                }

                return true
              },
            }}
            render={({ field, fieldState }) => (
              <Field
                required
                invalid={!!fieldState.error}
                errorText={fieldState.error?.message}
                label="Audience"
                labelEndElement={renderFieldInfo(
                  "Audience",
                  CREATOR_FIELD_HELP.audience,
                )}
                helperText={
                  fieldState.error
                    ? undefined
                    : "Select up to 5 audience segments."
                }
              >
                <MultiSelectOptionGroup
                  disabled={!isWorkflowUnlocked}
                  maxSelections={BRAND_INTELLIGENCE_LIMITS.audience}
                  onChange={field.onChange}
                  options={AUDIENCE_OPTIONS.map((option) => ({
                    label: option,
                    value: option,
                  }))}
                  value={field.value ?? []}
                />
              </Field>
            )}
          />

          <Grid
            mt={4}
            templateColumns={{ base: "1fr", lg: "repeat(2, 1fr)" }}
            gap={4}
          >
            <Controller
              control={control}
              name="primary_platforms"
              rules={{
                validate: (value) => {
                  if (!value || value.length === 0) {
                    return "Add at least 1 primary platform."
                  }

                  if (
                    value.length > BRAND_INTELLIGENCE_LIMITS.primaryPlatforms
                  ) {
                    return "Add up to 6 primary platforms."
                  }

                  return true
                },
              }}
              render={({ field, fieldState }) => (
                <Field
                  required
                  invalid={!!fieldState.error}
                  errorText={fieldState.error?.message}
                  label="Primary platforms"
                  labelEndElement={renderFieldInfo(
                    "Primary platforms",
                    CREATOR_FIELD_HELP.primary_platforms,
                  )}
                  helperText={
                    fieldState.error
                      ? undefined
                      : "Use one platform per line, up to 6."
                  }
                >
                  <Textarea
                    {...inputStyles}
                    aria-invalid={fieldState.error ? "true" : undefined}
                    disabled={!isWorkflowUnlocked}
                    minH="132px"
                    name={field.name}
                    onBlur={field.onBlur}
                    onChange={(event) => {
                      const nextValue = event.target.value
                      setTextInputValues((prev) => ({
                        ...prev,
                        primaryPlatforms: nextValue,
                      }))
                      field.onChange(normalizeTextareaListValues(nextValue))
                    }}
                    placeholder={"Instagram\nYouTube\nTikTok"}
                    ref={field.ref}
                    value={
                      creatorTextInputValues.primaryPlatforms ||
                      formatTextareaListValues(field.value)
                    }
                  />
                </Field>
              )}
            />

            <Controller
              control={control}
              name="collaborators_list"
              rules={{
                validate: (value) => {
                  if (
                    (value ?? []).length >
                    BRAND_INTELLIGENCE_LIMITS.collaborators
                  ) {
                    return "Add up to 10 collaborators."
                  }

                  return true
                },
              }}
              render={({ field, fieldState }) => (
                <Field
                  invalid={!!fieldState.error}
                  errorText={fieldState.error?.message}
                  label="Collaborators"
                  labelEndElement={renderFieldInfo(
                    "Collaborators",
                    CREATOR_FIELD_HELP.collaborators_list,
                  )}
                  helperText={
                    fieldState.error
                      ? undefined
                      : "Optional. Use one collaborator per line, up to 10."
                  }
                >
                  <Textarea
                    {...inputStyles}
                    aria-invalid={fieldState.error ? "true" : undefined}
                    disabled={!isWorkflowUnlocked}
                    minH="132px"
                    name={field.name}
                    onBlur={field.onBlur}
                    onChange={(event) => {
                      const nextValue = event.target.value
                      setTextInputValues((prev) => ({
                        ...prev,
                        collaborators: nextValue,
                      }))
                      field.onChange(normalizeTextareaListValues(nextValue))
                    }}
                    placeholder={"Brand One\nBrand Two\nManagement Partner"}
                    ref={field.ref}
                    value={
                      creatorTextInputValues.collaborators ||
                      formatTextareaListValues(field.value)
                    }
                  />
                </Field>
              )}
            />
          </Grid>

          <Grid
            mt={4}
            templateColumns={{ base: "1fr", lg: "repeat(2, 1fr)" }}
            gap={4}
          >
            <Controller
              control={control}
              name="reputation_signals.strengths"
              rules={buildSignalFieldRules("Strengths")}
              render={({ field, fieldState }) => (
                <Field
                  invalid={!!fieldState.error}
                  errorText={fieldState.error?.message}
                  label="Strengths"
                  labelEndElement={renderFieldInfo(
                    "Strengths",
                    REPUTATION_SIGNAL_FIELD_HELP.strengths,
                  )}
                  helperText={
                    <FieldHelperWithCounter
                      count={getTextareaLineMaxLength(
                        creatorTextInputValues.strengths ||
                          formatTextareaListValues(field.value),
                      )}
                      helperText="Per line"
                      limit={
                        BRAND_INTELLIGENCE_LIMITS.reputationSignalCharacters
                      }
                    />
                  }
                >
                  <Textarea
                    {...inputStyles}
                    aria-invalid={fieldState.error ? "true" : undefined}
                    disabled={!isWorkflowUnlocked}
                    minH="132px"
                    name={field.name}
                    onBlur={field.onBlur}
                    onChange={(event) => {
                      const nextValue = trimTextareaLineLength(
                        event.target.value,
                        BRAND_INTELLIGENCE_LIMITS.reputationSignalCharacters,
                      )
                      setTextInputValues((prev) => ({
                        ...prev,
                        strengths: nextValue,
                      }))
                      field.onChange(normalizeTextareaListValues(nextValue))
                    }}
                    placeholder={"Transparency\nConsistency\nClear voice"}
                    ref={field.ref}
                    value={
                      creatorTextInputValues.strengths ||
                      formatTextareaListValues(field.value)
                    }
                  />
                </Field>
              )}
            />

            <Controller
              control={control}
              name="reputation_signals.weaknesses"
              rules={buildSignalFieldRules("Weaknesses")}
              render={({ field, fieldState }) => (
                <Field
                  invalid={!!fieldState.error}
                  errorText={fieldState.error?.message}
                  label="Weaknesses"
                  labelEndElement={renderFieldInfo(
                    "Weaknesses",
                    REPUTATION_SIGNAL_FIELD_HELP.weaknesses,
                  )}
                  helperText={
                    <FieldHelperWithCounter
                      count={getTextareaLineMaxLength(
                        creatorTextInputValues.weaknesses ||
                          formatTextareaListValues(field.value),
                      )}
                      helperText="Per line"
                      limit={
                        BRAND_INTELLIGENCE_LIMITS.reputationSignalCharacters
                      }
                    />
                  }
                >
                  <Textarea
                    {...inputStyles}
                    aria-invalid={fieldState.error ? "true" : undefined}
                    disabled={!isWorkflowUnlocked}
                    minH="132px"
                    name={field.name}
                    onBlur={field.onBlur}
                    onChange={(event) => {
                      const nextValue = trimTextareaLineLength(
                        event.target.value,
                        BRAND_INTELLIGENCE_LIMITS.reputationSignalCharacters,
                      )
                      setTextInputValues((prev) => ({
                        ...prev,
                        weaknesses: nextValue,
                      }))
                      field.onChange(normalizeTextareaListValues(nextValue))
                    }}
                    placeholder={"Overexposure\nLow message clarity"}
                    ref={field.ref}
                    value={
                      creatorTextInputValues.weaknesses ||
                      formatTextareaListValues(field.value)
                    }
                  />
                </Field>
              )}
            />

            <Controller
              control={control}
              name="reputation_signals.incidents"
              rules={buildSignalFieldRules("Incidents")}
              render={({ field, fieldState }) => (
                <Field
                  invalid={!!fieldState.error}
                  errorText={fieldState.error?.message}
                  label="Incidents"
                  labelEndElement={renderFieldInfo(
                    "Incidents",
                    REPUTATION_SIGNAL_FIELD_HELP.incidents,
                  )}
                  helperText={
                    <FieldHelperWithCounter
                      count={getTextareaLineMaxLength(
                        creatorTextInputValues.incidents ||
                          formatTextareaListValues(field.value),
                      )}
                      helperText="Per line"
                      limit={
                        BRAND_INTELLIGENCE_LIMITS.reputationSignalCharacters
                      }
                    />
                  }
                >
                  <Textarea
                    {...inputStyles}
                    aria-invalid={fieldState.error ? "true" : undefined}
                    disabled={!isWorkflowUnlocked}
                    minH="132px"
                    name={field.name}
                    onBlur={field.onBlur}
                    onChange={(event) => {
                      const nextValue = trimTextareaLineLength(
                        event.target.value,
                        BRAND_INTELLIGENCE_LIMITS.reputationSignalCharacters,
                      )
                      setTextInputValues((prev) => ({
                        ...prev,
                        incidents: nextValue,
                      }))
                      field.onChange(normalizeTextareaListValues(nextValue))
                    }}
                    placeholder={"Content backlash\nPublic apology"}
                    ref={field.ref}
                    value={
                      creatorTextInputValues.incidents ||
                      formatTextareaListValues(field.value)
                    }
                  />
                </Field>
              )}
            />

            <Controller
              control={control}
              name="reputation_signals.concerns"
              rules={buildSignalFieldRules("Concerns")}
              render={({ field, fieldState }) => (
                <Field
                  invalid={!!fieldState.error}
                  errorText={fieldState.error?.message}
                  label="Concerns"
                  labelEndElement={renderFieldInfo(
                    "Concerns",
                    REPUTATION_SIGNAL_FIELD_HELP.concerns,
                  )}
                  helperText={
                    <FieldHelperWithCounter
                      count={getTextareaLineMaxLength(
                        creatorTextInputValues.concerns ||
                          formatTextareaListValues(field.value),
                      )}
                      helperText="Per line"
                      limit={
                        BRAND_INTELLIGENCE_LIMITS.reputationSignalCharacters
                      }
                    />
                  }
                >
                  <Textarea
                    {...inputStyles}
                    aria-invalid={fieldState.error ? "true" : undefined}
                    disabled={!isWorkflowUnlocked}
                    minH="132px"
                    name={field.name}
                    onBlur={field.onBlur}
                    onChange={(event) => {
                      const nextValue = trimTextareaLineLength(
                        event.target.value,
                        BRAND_INTELLIGENCE_LIMITS.reputationSignalCharacters,
                      )
                      setTextInputValues((prev) => ({
                        ...prev,
                        concerns: nextValue,
                      }))
                      field.onChange(normalizeTextareaListValues(nextValue))
                    }}
                    placeholder={"Collaboration fatigue\nUnclear boundaries"}
                    ref={field.ref}
                    value={
                      creatorTextInputValues.concerns ||
                      formatTextareaListValues(field.value)
                    }
                  />
                </Field>
              )}
            />
          </Grid>
        </StrategySection>

        {submitError ? (
          <Box
            rounded="3xl"
            borderWidth="1px"
            borderColor="ui.danger"
            bg="ui.dangerSoft"
            px={{ base: 5, md: 6 }}
            py={{ base: 4, md: 5 }}
          >
            <Flex alignItems="flex-start" gap={3}>
              <FiAlertCircle color="var(--chakra-colors-ui-dangerText)" />
              <Box>
                <Text color="ui.dangerText" fontWeight="black">
                  Report generation failed
                </Text>
                <Text mt={1} color="ui.secondaryText">
                  {submitError}
                </Text>
              </Box>
            </Flex>
          </Box>
        ) : null}

        {submitSuccess ? (
          <Box
            rounded="3xl"
            borderWidth="1px"
            borderColor="ui.brandBorderSoft"
            bg="ui.brandSoft"
            px={{ base: 5, md: 6 }}
            py={{ base: 4, md: 5 }}
          >
            <Text color="ui.brandText" fontWeight="black">
              Creator report generated
            </Text>
            <Text mt={1} color="ui.secondaryText">
              {submitSuccess}
            </Text>
          </Box>
        ) : null}

        <CreatorSubmitPanel
          control={control}
          creatorUsername={creatorUsername}
          invalidCreatorUsername={invalidCreatorUsername}
          isValidationPending={isValidationPending}
          isValidationStale={isValidationStale}
          missingUsernames={missingUsernames}
          orderedProfilesCount={orderedProfiles.length}
          reportIsPending={reportMutation.isPending}
        />
      </Flex>

      <CreatorStrategySummary
        control={control}
        creatorUsername={creatorUsername}
        expiredUsernames={expiredUsernames}
      />
    </Box>
  )
}

export default CreatorStrategyBuilder
