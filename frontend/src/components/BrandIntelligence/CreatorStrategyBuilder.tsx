import {
  Badge,
  Box,
  Flex,
  Grid,
  NativeSelect,
  Text,
  Textarea,
} from "@chakra-ui/react"
import { useMutation, useQueryClient } from "@tanstack/react-query"
import type { TFunction } from "i18next"
import { type Dispatch, type SetStateAction, useMemo, useState } from "react"
import {
  type Control,
  Controller,
  type FieldPath,
  type FieldValues,
  type UseFormReturn,
  useWatch,
} from "react-hook-form"
import { useTranslation } from "react-i18next"
import { FiAlertCircle, FiFileText, FiSearch } from "react-icons/fi"

import { Button } from "@/components/ui/button"
import { Field } from "@/components/ui/field"
import { TagsInputField } from "@/components/ui/tags-input-field"
import { invalidateBillingSummary } from "@/features/billing/api"
import {
  BRAND_INTELLIGENCE_CREATOR_ENDPOINT,
  generateBrandIntelligenceReport,
} from "@/features/brand-intelligence/api"
import {
  type AUDIENCE_OPTIONS,
  type CREATOR_GOAL_TYPE_OPTIONS,
  getAudienceLabel,
  getAudienceOptions,
  getCreatorGoalTypeLabel,
  getCreatorGoalTypeOptions,
  getTimeframeLabel,
  getTimeframeOptions,
  type TIMEFRAME_OPTIONS,
} from "@/features/brand-intelligence/catalogs"
import { BRAND_INTELLIGENCE_LIMITS } from "@/features/brand-intelligence/form-config"
import type {
  CreatorFormValues,
  CreatorTextInputValues,
} from "@/features/brand-intelligence/form-values"
import { buildCreatorStrategyPayload } from "@/features/brand-intelligence/form-values"
import type { useProfileExistenceValidation } from "@/features/brand-intelligence/use-profile-existence-validation"
import {
  isValidHttpUrl,
  normalizeListValues,
  normalizeUsernameList,
} from "@/features/brand-intelligence/utils"
import useCustomToast from "@/hooks/useCustomToast"
import { extractApiErrorMessage } from "@/lib/api-errors"
import { autofillIgnoreProps } from "@/lib/autofill"
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

const buildSignalFieldRules = (
  t: TFunction<"brandIntelligence">,
  fieldLabel: string,
) => ({
  validate: (value: string[] | undefined) => {
    if (
      (value ?? []).some(
        (entry) =>
          entry.length > BRAND_INTELLIGENCE_LIMITS.reputationSignalCharacters,
      )
    ) {
      return t("creator.validation.reputationSignalLineLimit", {
        count: BRAND_INTELLIGENCE_LIMITS.reputationSignalCharacters,
        label: fieldLabel,
      })
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
  const { t } = useTranslation("brandIntelligence")
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
      title: t("summary.sections.profileGate"),
      items: [
        {
          label: t("summary.items.creatorUsername"),
          value: creatorUsername ? [`@${creatorUsername}`] : [],
        },
        { label: t("summary.items.expiredProfiles"), value: expiredUsernames },
      ],
    },
    {
      title: t("summary.sections.creatorBrief"),
      items: [
        { label: t("summary.items.creatorContext"), value: creatorContext },
        { label: t("summary.items.creatorUrls"), value: normalizedCreatorUrls },
        {
          label: t("summary.items.goalType"),
          value: goalType
            ? getCreatorGoalTypeLabel(
                t,
                goalType as (typeof CREATOR_GOAL_TYPE_OPTIONS)[number],
              )
            : undefined,
        },
        { label: t("summary.items.goalContext"), value: goalContext },
        {
          label: t("summary.items.audience"),
          value: (audience ?? []).map((value) =>
            getAudienceLabel(t, value as (typeof AUDIENCE_OPTIONS)[number]),
          ),
        },
        {
          label: t("summary.items.timeframe"),
          value: timeframe
            ? getTimeframeLabel(
                t,
                timeframe as (typeof TIMEFRAME_OPTIONS)[number],
              )
            : undefined,
        },
      ],
    },
    {
      title: t("summary.sections.strategyInputs"),
      items: [
        {
          label: t("summary.items.primaryPlatforms"),
          value: normalizedPlatforms,
        },
        {
          label: t("summary.items.collaborators"),
          value: normalizedCollaborators,
        },
        {
          label: t("summary.items.strengths"),
          value: normalizedSignals.strengths,
        },
        {
          label: t("summary.items.weaknesses"),
          value: normalizedSignals.weaknesses,
        },
        {
          label: t("summary.items.incidents"),
          value: normalizedSignals.incidents,
        },
        {
          label: t("summary.items.concerns"),
          value: normalizedSignals.concerns,
        },
      ],
    },
  ]

  return (
    <StrategySummaryCard
      title={t("summary.creatorTitle")}
      sections={summarySections}
    />
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
  const { t } = useTranslation("brandIntelligence")
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
    ? t("creator.submitDisabledReason.missingUsername")
    : invalidCreatorUsername
      ? t("creator.submitDisabledReason.invalidUsername")
      : hasInvalidCreatorUrls
        ? t("creator.submitDisabledReason.invalidUrls")
        : !hasRequiredFields
          ? t("creator.submitDisabledReason.requiredFields")
          : isValidationPending
            ? t("creator.submitDisabledReason.validationPending")
            : isValidationStale || orderedProfilesCount === 0
              ? t("creator.submitDisabledReason.validationRequired")
              : missingUsernames.length > 0
                ? t("creator.submitDisabledReason.missingProfiles")
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
            {t("creator.submitPanel.title")}
          </Text>
          <Text mt={2} color="ui.secondaryText">
            {t("creator.submitPanel.description")}
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
          {t("creator.submitPanel.button")}
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
  const { t } = useTranslation("brandIntelligence")
  const queryClient = useQueryClient()
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
  const creatorGoalOptions = useMemo(() => getCreatorGoalTypeOptions(t), [t])
  const timeframeOptions = useMemo(() => getTimeframeOptions(t), [t])
  const audienceOptions = useMemo(() => getAudienceOptions(t), [t])

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
        throw new Error(t("creator.submitDisabledReason.missingProfiles"))
      }

      return generateBrandIntelligenceReport({
        endpointPath: BRAND_INTELLIGENCE_CREATOR_ENDPOINT,
        fallbackFilename: "reputation_creator_strategy.pdf",
        payload: buildCreatorStrategyPayload(values),
      })
    },
    onMutate: () => {
      setSubmitError(null)
      setSubmitSuccess(null)
    },
    onSuccess: async ({ blob, filename }) => {
      invalidateBillingSummary(queryClient)
      downloadBlob(blob, filename)
      setSubmitSuccess(t("creator.success.reportReady", { filename }))

      try {
        await saveLocalReport({
          blob,
          filename,
          reportType: "reputation-creator-strategy",
          source: "brand-intelligence",
        })
        showSuccessToast(t("creator.success.downloadedAndSaved"))
      } catch {
        showErrorToast(t("creator.success.downloadedOnly"))
      }
    },
    onError: (error) => {
      setSubmitError(
        extractApiErrorMessage(error, t("creator.errors.reportFailedFallback")),
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
      {...autofillIgnoreProps}
      onSubmit={handleSubmit(onSubmit)}
      display="grid"
      gridTemplateColumns={{ base: "1fr", xl: "minmax(0, 1.65fr) 360px" }}
      gap={6}
    >
      <Flex direction="column" gap={6} minW={0}>
        <StrategySection
          eyebrow={t("creator.step1.eyebrow")}
          title={t("creator.step1.title")}
          description={t("creator.step1.description")}
        >
          <Controller
            control={control}
            name="creator_username"
            rules={{
              validate: (value) => {
                const normalizedValue = normalizeUsernameList([value])[0] ?? ""

                if (!normalizedValue) {
                  return t("creator.validation.addCreatorUsername")
                }

                if (!isValidInstagramUsername(normalizedValue)) {
                  return t("campaign.validation.instagramUsername")
                }

                return true
              },
            }}
            render={({ field, fieldState }) => (
              <Field
                required
                invalid={!!fieldState.error}
                errorText={fieldState.error?.message}
                label={t("creator.fields.creatorUsername")}
                labelEndElement={renderFieldInfo(
                  t("creator.fields.creatorUsername"),
                  t("creator.fieldHelp.creatorUsername"),
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
                  placeholder={t("creator.placeholders.creatorUsername")}
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
              {t("creator.badges.usernameCount", {
                count: creatorUsername ? 1 : 0,
              })}
            </Badge>

            <Button
              type="button"
              variant="outline"
              onClick={handleValidateProfiles}
              disabled={!canRunValidation}
              loading={isValidationPending}
            >
              <FiSearch />
              {t("creator.actions.validateProfile")}
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
          eyebrow={t("creator.step2.eyebrow")}
          title={t("creator.step2.title")}
          description={t("creator.step2.description")}
        >
          <Grid templateColumns={{ base: "1fr", lg: "repeat(2, 1fr)" }} gap={4}>
            <Field
              required
              invalid={!!errors.goal_type}
              errorText={errors.goal_type?.message}
              label={t("creator.fields.goalType")}
              labelEndElement={renderFieldInfo(
                t("creator.fields.goalType"),
                t("creator.fieldHelp.goalType"),
              )}
            >
              <NativeSelect.Root disabled={!isWorkflowUnlocked}>
                <NativeSelect.Field
                  {...register("goal_type", {
                    required: t("creator.validation.selectGoalType"),
                  })}
                  {...autofillIgnoreProps}
                  {...inputStyles}
                >
                  <option value="">{t("creator.select.goal")}</option>
                  {creatorGoalOptions.map((option) => (
                    <option key={option.value} value={option.value}>
                      {option.label}
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
              label={t("creator.fields.timeframe")}
              labelEndElement={renderFieldInfo(
                t("creator.fields.timeframe"),
                t("creator.fieldHelp.timeframe"),
              )}
            >
              <NativeSelect.Root disabled={!isWorkflowUnlocked}>
                <NativeSelect.Field
                  {...register("timeframe", {
                    required: t("creator.validation.selectTimeframe"),
                  })}
                  {...autofillIgnoreProps}
                  {...inputStyles}
                >
                  <option value="">{t("creator.select.timeframe")}</option>
                  {timeframeOptions.map((option) => (
                    <option key={option.value} value={option.value}>
                      {option.label}
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
              label={t("creator.fields.creatorContext")}
              labelEndElement={renderFieldInfo(
                t("creator.fields.creatorContext"),
                t("creator.fieldHelp.creatorContext"),
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
                  required: t("creator.validation.creatorContextRequired"),
                  maxLength: {
                    value: 500,
                    message: t("creator.validation.maxCharacters", {
                      count: 500,
                    }),
                  },
                })}
                {...autofillIgnoreProps}
                {...inputStyles}
                disabled={!isWorkflowUnlocked}
                maxLength={500}
                minH="132px"
                placeholder={t("creator.placeholders.creatorContext")}
              />
            </Field>

            <Field
              required
              invalid={!!errors.goal_context}
              errorText={errors.goal_context?.message}
              label={t("creator.fields.goalContext")}
              labelEndElement={renderFieldInfo(
                t("creator.fields.goalContext"),
                t("creator.fieldHelp.goalContext"),
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
                  required: t("creator.validation.goalContextRequired"),
                  maxLength: {
                    value: 500,
                    message: t("creator.validation.maxCharacters", {
                      count: 500,
                    }),
                  },
                })}
                {...autofillIgnoreProps}
                {...inputStyles}
                disabled={!isWorkflowUnlocked}
                maxLength={500}
                minH="132px"
                placeholder={t("creator.placeholders.goalContext")}
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
                    return t("creator.validation.creatorUrlsLimit")
                  }

                  if ((value ?? []).some((url) => !isValidHttpUrl(url))) {
                    return t("creator.submitDisabledReason.invalidUrls")
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
                    label={t("creator.fields.creatorUrls")}
                    labelEndElement={renderFieldInfo(
                      t("creator.fields.creatorUrls"),
                      t("creator.fieldHelp.creatorUrls"),
                    )}
                    helperText={
                      fieldState.error
                        ? undefined
                        : t("creator.helperText.creatorUrls")
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
                      placeholder={t("creator.placeholders.creatorUrls")}
                      value={field.value ?? []}
                    />
                  </Field>
                )
              }}
            />
          </Box>
        </StrategySection>

        <StrategySection
          eyebrow={t("creator.step3.eyebrow")}
          title={t("creator.step3.title")}
          description={t("creator.step3.description")}
        >
          <Controller
            control={control}
            name="audience"
            rules={{
              validate: (value) => {
                if (!value || value.length === 0) {
                  return t("creator.validation.selectAudience")
                }

                if (value.length > BRAND_INTELLIGENCE_LIMITS.audience) {
                  return t("creator.validation.audienceLimit")
                }

                return true
              },
            }}
            render={({ field, fieldState }) => (
              <Field
                required
                invalid={!!fieldState.error}
                errorText={fieldState.error?.message}
                label={t("creator.fields.audience")}
                labelEndElement={renderFieldInfo(
                  t("creator.fields.audience"),
                  t("creator.fieldHelp.audience"),
                )}
                helperText={
                  fieldState.error
                    ? undefined
                    : t("creator.helperText.audience")
                }
              >
                <MultiSelectOptionGroup
                  disabled={!isWorkflowUnlocked}
                  maxSelections={BRAND_INTELLIGENCE_LIMITS.audience}
                  onChange={field.onChange}
                  options={audienceOptions}
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
                    return t("creator.validation.primaryPlatformsRequired")
                  }

                  if (
                    value.length > BRAND_INTELLIGENCE_LIMITS.primaryPlatforms
                  ) {
                    return t("creator.validation.primaryPlatformsLimit")
                  }

                  return true
                },
              }}
              render={({ field, fieldState }) => (
                <Field
                  required
                  invalid={!!fieldState.error}
                  errorText={fieldState.error?.message}
                  label={t("creator.fields.primaryPlatforms")}
                  labelEndElement={renderFieldInfo(
                    t("creator.fields.primaryPlatforms"),
                    t("creator.fieldHelp.primaryPlatforms"),
                  )}
                  helperText={
                    fieldState.error
                      ? undefined
                      : t("creator.helperText.primaryPlatforms")
                  }
                >
                  <Textarea
                    {...autofillIgnoreProps}
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
                    placeholder={t("creator.placeholders.primaryPlatforms")}
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
                    return t("creator.validation.collaboratorsLimit")
                  }

                  return true
                },
              }}
              render={({ field, fieldState }) => (
                <Field
                  invalid={!!fieldState.error}
                  errorText={fieldState.error?.message}
                  label={t("creator.fields.collaborators")}
                  labelEndElement={renderFieldInfo(
                    t("creator.fields.collaborators"),
                    t("creator.fieldHelp.collaborators"),
                  )}
                  helperText={
                    fieldState.error
                      ? undefined
                      : t("creator.helperText.collaborators")
                  }
                >
                  <Textarea
                    {...autofillIgnoreProps}
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
                    placeholder={t("creator.placeholders.collaborators")}
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
              rules={buildSignalFieldRules(t, t("creator.fields.strengths"))}
              render={({ field, fieldState }) => (
                <Field
                  invalid={!!fieldState.error}
                  errorText={fieldState.error?.message}
                  label={t("creator.fields.strengths")}
                  labelEndElement={renderFieldInfo(
                    t("creator.fields.strengths"),
                    t("creator.fieldHelp.strengths"),
                  )}
                  helperText={
                    <FieldHelperWithCounter
                      count={getTextareaLineMaxLength(
                        creatorTextInputValues.strengths ||
                          formatTextareaListValues(field.value),
                      )}
                      helperText={t("creator.helperText.perLine")}
                      limit={
                        BRAND_INTELLIGENCE_LIMITS.reputationSignalCharacters
                      }
                    />
                  }
                >
                  <Textarea
                    {...autofillIgnoreProps}
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
                    placeholder={t("creator.placeholders.strengths")}
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
              rules={buildSignalFieldRules(t, t("creator.fields.weaknesses"))}
              render={({ field, fieldState }) => (
                <Field
                  invalid={!!fieldState.error}
                  errorText={fieldState.error?.message}
                  label={t("creator.fields.weaknesses")}
                  labelEndElement={renderFieldInfo(
                    t("creator.fields.weaknesses"),
                    t("creator.fieldHelp.weaknesses"),
                  )}
                  helperText={
                    <FieldHelperWithCounter
                      count={getTextareaLineMaxLength(
                        creatorTextInputValues.weaknesses ||
                          formatTextareaListValues(field.value),
                      )}
                      helperText={t("creator.helperText.perLine")}
                      limit={
                        BRAND_INTELLIGENCE_LIMITS.reputationSignalCharacters
                      }
                    />
                  }
                >
                  <Textarea
                    {...autofillIgnoreProps}
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
                    placeholder={t("creator.placeholders.weaknesses")}
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
              rules={buildSignalFieldRules(t, t("creator.fields.incidents"))}
              render={({ field, fieldState }) => (
                <Field
                  invalid={!!fieldState.error}
                  errorText={fieldState.error?.message}
                  label={t("creator.fields.incidents")}
                  labelEndElement={renderFieldInfo(
                    t("creator.fields.incidents"),
                    t("creator.fieldHelp.incidents"),
                  )}
                  helperText={
                    <FieldHelperWithCounter
                      count={getTextareaLineMaxLength(
                        creatorTextInputValues.incidents ||
                          formatTextareaListValues(field.value),
                      )}
                      helperText={t("creator.helperText.perLine")}
                      limit={
                        BRAND_INTELLIGENCE_LIMITS.reputationSignalCharacters
                      }
                    />
                  }
                >
                  <Textarea
                    {...autofillIgnoreProps}
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
                    placeholder={t("creator.placeholders.incidents")}
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
              rules={buildSignalFieldRules(t, t("creator.fields.concerns"))}
              render={({ field, fieldState }) => (
                <Field
                  invalid={!!fieldState.error}
                  errorText={fieldState.error?.message}
                  label={t("creator.fields.concerns")}
                  labelEndElement={renderFieldInfo(
                    t("creator.fields.concerns"),
                    t("creator.fieldHelp.concerns"),
                  )}
                  helperText={
                    <FieldHelperWithCounter
                      count={getTextareaLineMaxLength(
                        creatorTextInputValues.concerns ||
                          formatTextareaListValues(field.value),
                      )}
                      helperText={t("creator.helperText.perLine")}
                      limit={
                        BRAND_INTELLIGENCE_LIMITS.reputationSignalCharacters
                      }
                    />
                  }
                >
                  <Textarea
                    {...autofillIgnoreProps}
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
                    placeholder={t("creator.placeholders.concerns")}
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
                  {t("creator.errors.reportFailedTitle")}
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
              {t("creator.success.statusTitle")}
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
