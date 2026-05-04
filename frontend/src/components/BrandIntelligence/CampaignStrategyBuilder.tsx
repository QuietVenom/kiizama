import {
  Badge,
  Box,
  Flex,
  Grid,
  HStack,
  Input,
  NativeSelect,
  Text,
  Textarea,
} from "@chakra-ui/react"
import { useMutation, useQueryClient } from "@tanstack/react-query"
import { useEffect, useMemo, useState } from "react"
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

import UsernameTagsInput from "@/components/CreatorsSearch/UsernameTagsInput"
import { Button } from "@/components/ui/button"
import { Checkbox } from "@/components/ui/checkbox"
import { Field } from "@/components/ui/field"
import { TagsInputField } from "@/components/ui/tags-input-field"
import { invalidateBillingSummary } from "@/features/billing/api"
import {
  BRAND_INTELLIGENCE_CAMPAIGN_ENDPOINT,
  generateBrandIntelligenceReport,
} from "@/features/brand-intelligence/api"
import {
  type AUDIENCE_OPTIONS,
  type BRAND_GOALS_TYPE_OPTIONS,
  type CAMPAIGN_TYPE_OPTIONS,
  getAudienceLabel,
  getAudienceOptions,
  getBrandGoalTypeLabel,
  getBrandGoalTypeOptions,
  getCampaignTypeContent,
  getCampaignTypeOptions,
  getTimeframeLabel,
  getTimeframeOptions,
  type TIMEFRAME_OPTIONS,
} from "@/features/brand-intelligence/catalogs"
import { BRAND_INTELLIGENCE_LIMITS } from "@/features/brand-intelligence/form-config"
import {
  buildCampaignStrategyPayload,
  type CampaignFormValues,
} from "@/features/brand-intelligence/form-values"
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

type CampaignStrategyBuilderProps = {
  form: UseFormReturn<CampaignFormValues>
  normalizedProfiles: string[]
  validation: ReturnType<typeof useProfileExistenceValidation>
}

const inputStyles = {
  bg: "ui.panel",
  borderColor: "ui.sidebarBorder",
  rounded: "2xl",
} as const

const CRISIS_BRAND_GOAL = "Crisis"

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

const CampaignTypePreview = ({
  control,
}: {
  control: Control<CampaignFormValues>
}) => {
  const { t } = useTranslation("brandIntelligence")
  const campaignType = useWatch({ control, name: "campaign_type" })
  const selectedCampaignType = useMemo(
    () =>
      campaignType
        ? getCampaignTypeContent(
            t,
            campaignType as (typeof CAMPAIGN_TYPE_OPTIONS)[number]["name"],
          )
        : null,
    [campaignType, t],
  )

  if (!selectedCampaignType) {
    return null
  }

  return (
    <Box
      mt={4}
      rounded="2xl"
      borderWidth="1px"
      borderColor="ui.brandBorderSoft"
      bg="ui.brandSoft"
      px={4}
      py={4}
    >
      <Text fontWeight="bold" color="ui.brandText">
        {selectedCampaignType.title}
      </Text>
      <Text mt={1.5} color="ui.secondaryText">
        {selectedCampaignType.description}
      </Text>
    </Box>
  )
}

const CampaignStrategySummary = ({
  control,
  expiredUsernames,
  isNotUsingCreators,
  normalizedProfiles,
}: {
  control: Control<CampaignFormValues>
  expiredUsernames: string[]
  isNotUsingCreators: boolean
  normalizedProfiles: string[]
}) => {
  const { t } = useTranslation("brandIntelligence")
  const [
    audience,
    brandContext,
    brandGoalsContext,
    brandGoalsType,
    brandName,
    brandUrls,
    campaignType,
    timeframe,
  ] = useWatch({
    control,
    name: [
      "audience",
      "brand_context",
      "brand_goals_context",
      "brand_goals_type",
      "brand_name",
      "brand_urls",
      "campaign_type",
      "timeframe",
    ],
  })

  const normalizedBrandUrls = useMemo(
    () => normalizeListValues(brandUrls ?? []),
    [brandUrls],
  )
  const selectedCampaignType = useMemo(
    () =>
      campaignType
        ? getCampaignTypeContent(
            t,
            campaignType as (typeof CAMPAIGN_TYPE_OPTIONS)[number]["name"],
          )
        : null,
    [campaignType, t],
  )

  const summarySections = [
    {
      title: t("summary.sections.creatorsGate"),
      items: [
        {
          label: t("summary.items.creatorUsage"),
          value: isNotUsingCreators
            ? t("summary.values.notUsingCreators")
            : undefined,
        },
        {
          label: t("summary.items.creatorUsernames"),
          value: isNotUsingCreators ? [] : normalizedProfiles,
        },
        {
          label: t("summary.items.expiredProfiles"),
          value: isNotUsingCreators ? [] : expiredUsernames,
        },
      ],
    },
    {
      title: t("summary.sections.brandBrief"),
      items: [
        { label: t("summary.items.brandName"), value: brandName },
        { label: t("summary.items.brandContext"), value: brandContext },
        { label: t("summary.items.brandUrls"), value: normalizedBrandUrls },
        {
          label: t("summary.items.brandGoal"),
          value: brandGoalsType
            ? getBrandGoalTypeLabel(
                t,
                brandGoalsType as (typeof BRAND_GOALS_TYPE_OPTIONS)[number],
              )
            : undefined,
        },
        { label: t("summary.items.goalContext"), value: brandGoalsContext },
      ],
    },
    {
      title: t("summary.sections.campaignSetup"),
      items: [
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
        {
          label: t("summary.items.campaignType"),
          value: selectedCampaignType?.title,
        },
        {
          label: t("summary.items.campaignTypeContext"),
          value: selectedCampaignType?.description,
        },
      ],
    },
  ]

  return (
    <StrategySummaryCard
      title={t("summary.campaignTitle")}
      sections={summarySections}
    />
  )
}

const CampaignSubmitPanel = ({
  control,
  invalidUsernames,
  isNotUsingCreators,
  isValidationPending,
  isValidationStale,
  missingUsernames,
  normalizedProfiles,
  orderedProfilesCount,
  reportIsPending,
}: {
  control: Control<CampaignFormValues>
  invalidUsernames: string[]
  isNotUsingCreators: boolean
  isValidationPending: boolean
  isValidationStale: boolean
  missingUsernames: string[]
  normalizedProfiles: string[]
  orderedProfilesCount: number
  reportIsPending: boolean
}) => {
  const { t } = useTranslation("brandIntelligence")
  const [
    audience,
    brandContext,
    brandGoalsContext,
    brandGoalsType,
    brandName,
    brandUrls,
    campaignType,
    timeframe,
  ] = useWatch({
    control,
    name: [
      "audience",
      "brand_context",
      "brand_goals_context",
      "brand_goals_type",
      "brand_name",
      "brand_urls",
      "campaign_type",
      "timeframe",
    ],
  })

  const normalizedBrandUrls = useMemo(
    () => normalizeListValues(brandUrls ?? []),
    [brandUrls],
  )
  const hasInvalidBrandUrls = normalizedBrandUrls.some(
    (value) => !isValidHttpUrl(value),
  )
  const hasRequiredFields =
    (isNotUsingCreators || normalizedProfiles.length > 0) &&
    Boolean(brandName) &&
    Boolean(brandContext) &&
    Boolean(brandGoalsContext) &&
    Boolean(brandGoalsType) &&
    Boolean(campaignType) &&
    Boolean(timeframe) &&
    (audience?.length ?? 0) > 0

  const submitDisabledReason =
    !isNotUsingCreators && normalizedProfiles.length === 0
      ? t("campaign.submitDisabledReason.missingUsernames")
      : !isNotUsingCreators && invalidUsernames.length > 0
        ? t("campaign.submitDisabledReason.invalidUsernames")
        : hasInvalidBrandUrls
          ? t("campaign.submitDisabledReason.invalidUrls")
          : !hasRequiredFields
            ? t("campaign.submitDisabledReason.requiredFields")
            : !isNotUsingCreators && isValidationPending
              ? t("campaign.submitDisabledReason.validationPending")
              : !isNotUsingCreators &&
                  (isValidationStale || orderedProfilesCount === 0)
                ? t("campaign.submitDisabledReason.validationRequired")
                : !isNotUsingCreators && missingUsernames.length > 0
                  ? t("campaign.submitDisabledReason.missingProfiles")
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
            {t("campaign.submitPanel.title")}
          </Text>
          <Text mt={2} color="ui.secondaryText">
            {t("campaign.submitPanel.description")}
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
          {t("campaign.submitPanel.button")}
        </Button>
      </Flex>
    </Box>
  )
}

const CampaignStrategyBuilder = ({
  form,
  normalizedProfiles,
  validation,
}: CampaignStrategyBuilderProps) => {
  const { t } = useTranslation("brandIntelligence")
  const queryClient = useQueryClient()
  const { showErrorToast, showSuccessToast } = useCustomToast()
  const [submitError, setSubmitError] = useState<string | null>(null)
  const [submitSuccess, setSubmitSuccess] = useState<string | null>(null)
  const [notUsingCreators, setNotUsingCreators] = useState(false)

  const {
    clearErrors,
    control,
    formState: { errors },
    handleSubmit,
    register,
    setValue,
    trigger,
  } = form
  const brandGoalsType = useWatch({
    control,
    name: "brand_goals_type",
    defaultValue: "",
  })
  const isCrisisGoal = brandGoalsType === CRISIS_BRAND_GOAL
  const isNotUsingCreators = isCrisisGoal && notUsingCreators

  useEffect(() => {
    if (!isCrisisGoal) {
      setNotUsingCreators(false)
    }
  }, [isCrisisGoal])

  useEffect(() => {
    if (isNotUsingCreators) {
      clearErrors("profiles_list")
    }
  }, [clearErrors, isNotUsingCreators])

  const invalidUsernames = useMemo(
    () =>
      isNotUsingCreators
        ? []
        : normalizedProfiles.filter(
            (username) => !isValidInstagramUsername(username),
          ),
    [isNotUsingCreators, normalizedProfiles],
  )
  const invalidUsernameSet = useMemo(
    () => new Set(invalidUsernames),
    [invalidUsernames],
  )

  const {
    expiredUsernames,
    isValidationPending,
    isValidationStale,
    missingUsernames,
    orderedProfiles,
    validateProfiles,
    validationError,
  } = validation

  const isWorkflowUnlocked = normalizedProfiles.length > 0 || isNotUsingCreators
  const canRunValidation =
    !isNotUsingCreators &&
    normalizedProfiles.length > 0 &&
    invalidUsernames.length === 0 &&
    !isValidationPending
  const brandGoalOptions = useMemo(() => getBrandGoalTypeOptions(t), [t])
  const timeframeOptions = useMemo(() => getTimeframeOptions(t), [t])
  const campaignTypeOptions = useMemo(() => getCampaignTypeOptions(t), [t])
  const audienceOptions = useMemo(() => getAudienceOptions(t), [t])

  const handleValidateProfiles = async () => {
    if (isNotUsingCreators) return

    setSubmitError(null)
    setSubmitSuccess(null)
    setValue("profiles_list", normalizedProfiles, {
      shouldDirty: true,
      shouldValidate: true,
    })

    const isFieldValid = await trigger("profiles_list")
    if (!isFieldValid) return

    await validateProfiles(normalizedProfiles)
  }

  const reportMutation = useMutation({
    mutationFn: async (values: CampaignFormValues) => {
      const normalizedRequestProfiles = normalizeUsernameList(
        values.profiles_list,
      )
      const profilesList = isNotUsingCreators ? [] : normalizedRequestProfiles

      if (!isNotUsingCreators) {
        const validationResult = await validateProfiles(profilesList)
        const missingProfiles = (validationResult?.profiles ?? [])
          .filter((profile) => !profile.exists)
          .map((profile) => profile.username)

        if (missingProfiles.length > 0) {
          throw new Error(t("campaign.submitDisabledReason.missingProfiles"))
        }
      }

      return generateBrandIntelligenceReport({
        endpointPath: BRAND_INTELLIGENCE_CAMPAIGN_ENDPOINT,
        fallbackFilename: "reputation_campaign_strategy.pdf",
        payload: buildCampaignStrategyPayload(values, { profilesList }),
      })
    },
    onMutate: () => {
      setSubmitError(null)
      setSubmitSuccess(null)
    },
    onSuccess: async ({ blob, filename }) => {
      invalidateBillingSummary(queryClient)
      downloadBlob(blob, filename)
      setSubmitSuccess(t("campaign.success.reportReady", { filename }))

      try {
        await saveLocalReport({
          blob,
          filename,
          reportType: "reputation-campaign-strategy",
          source: "brand-intelligence",
        })
        showSuccessToast(t("campaign.success.downloadedAndSaved"))
      } catch {
        showErrorToast(t("campaign.success.downloadedOnly"))
      }
    },
    onError: (error) => {
      setSubmitError(
        extractApiErrorMessage(
          error,
          t("campaign.errors.reportFailedFallback"),
        ),
      )
    },
  })

  const onSubmit = (values: CampaignFormValues) => {
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
          eyebrow={t("campaign.step1.eyebrow")}
          title={t("campaign.step1.title")}
          description={t("campaign.step1.description")}
        >
          <Field
            required
            invalid={!!errors.brand_goals_type}
            errorText={errors.brand_goals_type?.message}
            label={t("campaign.fields.brandGoal")}
            labelEndElement={renderFieldInfo(
              t("campaign.fields.brandGoal"),
              t("campaign.fieldHelp.brandGoal"),
            )}
          >
            <NativeSelect.Root>
              <NativeSelect.Field
                {...register("brand_goals_type", {
                  required: t("campaign.validation.selectBrandGoal"),
                })}
                {...autofillIgnoreProps}
                {...inputStyles}
              >
                <option value="">{t("campaign.select.goal")}</option>
                {brandGoalOptions.map((option) => (
                  <option key={option.value} value={option.value}>
                    {option.label}
                  </option>
                ))}
              </NativeSelect.Field>
              <NativeSelect.Indicator />
            </NativeSelect.Root>
          </Field>

          <Controller
            control={control}
            name="profiles_list"
            rules={{
              validate: (value) => {
                if (isNotUsingCreators) {
                  return true
                }

                if (!value || value.length === 0) {
                  return t("campaign.validation.addCreatorUsername")
                }

                if (value.length > BRAND_INTELLIGENCE_LIMITS.campaignProfiles) {
                  return t("campaign.validation.creatorUsernamesLimit")
                }

                if (
                  value.some((username) => !isValidInstagramUsername(username))
                ) {
                  return t("campaign.validation.instagramUsername")
                }

                return true
              },
            }}
            render={({ field, fieldState }) => (
              <Field
                required={!isNotUsingCreators}
                invalid={!!fieldState.error}
                errorText={fieldState.error?.message}
                label={t("campaign.fields.creatorUsernames")}
                labelEndElement={renderFieldInfo(
                  t("campaign.fields.creatorUsernames"),
                  t("campaign.fieldHelp.creatorUsernames"),
                )}
                helperText={
                  fieldState.error
                    ? undefined
                    : isNotUsingCreators
                      ? t("campaign.helperText.creatorsDisabled")
                      : t("campaign.helperText.creatorUsernames")
                }
              >
                <UsernameTagsInput
                  disabled={isNotUsingCreators}
                  expiredValues={new Set(expiredUsernames)}
                  invalid={!!fieldState.error}
                  invalidValues={invalidUsernameSet}
                  missingValues={new Set(missingUsernames)}
                  onValueChange={(nextValue) =>
                    field.onChange(normalizeUsernameList(nextValue))
                  }
                  placeholder={t("campaign.placeholders.creatorUsernames")}
                  value={field.value}
                />
              </Field>
            )}
          />

          <Field
            mt={4}
            helperText={
              isCrisisGoal
                ? t("campaign.helperText.crisisOnly")
                : t("campaign.helperText.enableCrisisOnly")
            }
          >
            <Checkbox
              checked={notUsingCreators}
              disabled={!isCrisisGoal}
              onCheckedChange={({ checked }) =>
                setNotUsingCreators(Boolean(checked))
              }
            >
              {t("campaign.fields.notUsingCreators")}
            </Checkbox>
          </Field>

          <Flex
            mt={4}
            alignItems="center"
            justifyContent="space-between"
            gap={3}
            wrap="wrap"
          >
            <HStack gap={2} wrap="wrap">
              {isNotUsingCreators ? (
                <Badge
                  rounded="full"
                  bg="ui.brandSoft"
                  color="ui.brandText"
                  px={3}
                  py={1.5}
                >
                  {t("campaign.badges.creatorsNotRequired")}
                </Badge>
              ) : (
                <Badge
                  rounded="full"
                  borderWidth="1px"
                  borderColor="ui.border"
                  bg="ui.surfaceSoft"
                  color="ui.secondaryText"
                  px={3}
                  py={1.5}
                >
                  {t("campaign.badges.creatorUsernamesCount", {
                    count: normalizedProfiles.length,
                    limit: BRAND_INTELLIGENCE_LIMITS.campaignProfiles,
                  })}
                </Badge>
              )}
              {isWorkflowUnlocked ? (
                <Badge
                  rounded="full"
                  bg="ui.brandSoft"
                  color="ui.brandText"
                  px={3}
                  py={1.5}
                >
                  {t("campaign.badges.workflowUnlocked")}
                </Badge>
              ) : null}
            </HStack>

            {isNotUsingCreators ? null : (
              <Button
                type="button"
                variant="outline"
                onClick={handleValidateProfiles}
                disabled={!canRunValidation}
                loading={isValidationPending}
              >
                <FiSearch />
                {t("campaign.actions.validateProfiles")}
              </Button>
            )}
          </Flex>

          <Box mt={4}>
            {isNotUsingCreators ? (
              <Box
                rounded="3xl"
                borderWidth="1px"
                borderColor="ui.brandBorderSoft"
                bg="ui.brandSoft"
                px={5}
                py={5}
              >
                <Text fontWeight="bold" color="ui.brandText">
                  {t("campaign.skippedValidation.title")}
                </Text>
                <Text mt={2} color="ui.secondaryText">
                  {t("campaign.skippedValidation.description")}
                </Text>
              </Box>
            ) : (
              <ProfileValidationPanel
                error={validationError}
                isLoading={isValidationPending}
                isStale={isValidationStale}
                profiles={orderedProfiles}
                usernames={normalizedProfiles}
              />
            )}
          </Box>
        </StrategySection>

        <StrategySection
          eyebrow={t("campaign.step2.eyebrow")}
          title={t("campaign.step2.title")}
          description={t("campaign.step2.description")}
        >
          <Field
            required
            invalid={!!errors.brand_name}
            errorText={errors.brand_name?.message}
            label={t("campaign.fields.brandName")}
            labelEndElement={renderFieldInfo(
              t("campaign.fields.brandName"),
              t("campaign.fieldHelp.brandName"),
            )}
            helperText={
              <CharacterCountHelper
                control={control}
                name="brand_name"
                limit={120}
              />
            }
          >
            <Input
              {...register("brand_name", {
                required: t("campaign.validation.brandNameRequired"),
                maxLength: {
                  value: 120,
                  message: t("campaign.validation.maxCharacters", {
                    count: 120,
                  }),
                },
              })}
              {...autofillIgnoreProps}
              {...inputStyles}
              disabled={!isWorkflowUnlocked}
              maxLength={120}
              placeholder={t("campaign.placeholders.brandName")}
            />
          </Field>

          <Grid
            mt={4}
            templateColumns={{ base: "1fr", lg: "repeat(2, 1fr)" }}
            gap={4}
          >
            <Field
              required
              invalid={!!errors.brand_context}
              errorText={errors.brand_context?.message}
              label={t("campaign.fields.brandContext")}
              labelEndElement={renderFieldInfo(
                t("campaign.fields.brandContext"),
                t("campaign.fieldHelp.brandContext"),
              )}
              helperText={
                <CharacterCountHelper
                  control={control}
                  name="brand_context"
                  limit={500}
                />
              }
            >
              <Textarea
                {...register("brand_context", {
                  required: t("campaign.validation.brandContextRequired"),
                  maxLength: {
                    value: 500,
                    message: t("campaign.validation.maxCharacters", {
                      count: 500,
                    }),
                  },
                })}
                {...autofillIgnoreProps}
                {...inputStyles}
                disabled={!isWorkflowUnlocked}
                maxLength={500}
                minH="132px"
                placeholder={t("campaign.placeholders.brandContext")}
              />
            </Field>

            <Field
              required
              invalid={!!errors.brand_goals_context}
              errorText={errors.brand_goals_context?.message}
              label={t("campaign.fields.goalContext")}
              labelEndElement={renderFieldInfo(
                t("campaign.fields.goalContext"),
                t("campaign.fieldHelp.goalContext"),
              )}
              helperText={
                <CharacterCountHelper
                  control={control}
                  name="brand_goals_context"
                  limit={500}
                />
              }
            >
              <Textarea
                {...register("brand_goals_context", {
                  required: t("campaign.validation.goalContextRequired"),
                  maxLength: {
                    value: 500,
                    message: t("campaign.validation.maxCharacters", {
                      count: 500,
                    }),
                  },
                })}
                {...autofillIgnoreProps}
                {...inputStyles}
                disabled={!isWorkflowUnlocked}
                maxLength={500}
                minH="132px"
                placeholder={t("campaign.placeholders.goalContext")}
              />
            </Field>
          </Grid>

          <Box mt={4}>
            <Controller
              control={control}
              name="brand_urls"
              rules={{
                validate: (value) => {
                  if (
                    (value ?? []).length > BRAND_INTELLIGENCE_LIMITS.brandUrls
                  ) {
                    return t("campaign.validation.brandUrlsLimit")
                  }

                  if ((value ?? []).some((url) => !isValidHttpUrl(url))) {
                    return t("campaign.submitDisabledReason.invalidUrls")
                  }

                  return true
                },
              }}
              render={({ field, fieldState }) => {
                const normalizedBrandUrls = normalizeListValues(
                  field.value ?? [],
                )
                const invalidBrandUrlSet = new Set(
                  normalizedBrandUrls.filter((value) => !isValidHttpUrl(value)),
                )

                return (
                  <Field
                    invalid={!!fieldState.error}
                    errorText={fieldState.error?.message}
                    label={t("campaign.fields.brandUrls")}
                    labelEndElement={renderFieldInfo(
                      t("campaign.fields.brandUrls"),
                      t("campaign.fieldHelp.brandUrls"),
                    )}
                    helperText={
                      fieldState.error
                        ? undefined
                        : t("campaign.helperText.brandUrls")
                    }
                  >
                    <TagsInputField
                      disabled={!isWorkflowUnlocked}
                      getTagPalette={(value) =>
                        getUrlPalette(invalidBrandUrlSet, value)
                      }
                      invalid={!!fieldState.error}
                      max={BRAND_INTELLIGENCE_LIMITS.brandUrls}
                      onValueChange={(nextValue) =>
                        field.onChange(normalizeListValues(nextValue))
                      }
                      placeholder={t("campaign.placeholders.brandUrls")}
                      value={field.value ?? []}
                    />
                  </Field>
                )
              }}
            />
          </Box>
        </StrategySection>

        <StrategySection
          eyebrow={t("campaign.step3.eyebrow")}
          title={t("campaign.step3.title")}
          description={t("campaign.step3.description")}
        >
          <Grid templateColumns={{ base: "1fr", lg: "repeat(2, 1fr)" }} gap={4}>
            <Field
              required
              invalid={!!errors.timeframe}
              errorText={errors.timeframe?.message}
              label={t("campaign.fields.timeframe")}
              labelEndElement={renderFieldInfo(
                t("campaign.fields.timeframe"),
                t("campaign.fieldHelp.timeframe"),
              )}
            >
              <NativeSelect.Root disabled={!isWorkflowUnlocked}>
                <NativeSelect.Field
                  {...register("timeframe", {
                    required: t("campaign.validation.selectTimeframe"),
                  })}
                  {...autofillIgnoreProps}
                  {...inputStyles}
                >
                  <option value="">{t("campaign.select.timeframe")}</option>
                  {timeframeOptions.map((option) => (
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
              invalid={!!errors.campaign_type}
              errorText={errors.campaign_type?.message}
              label={t("campaign.fields.campaignType")}
              labelEndElement={renderFieldInfo(
                t("campaign.fields.campaignType"),
                t("campaign.fieldHelp.campaignType"),
              )}
            >
              <NativeSelect.Root disabled={!isWorkflowUnlocked}>
                <NativeSelect.Field
                  {...register("campaign_type", {
                    required: t("campaign.validation.selectCampaignType"),
                  })}
                  {...autofillIgnoreProps}
                  {...inputStyles}
                >
                  <option value="">{t("campaign.select.campaignModel")}</option>
                  {campaignTypeOptions.map((option) => (
                    <option key={option.value} value={option.value}>
                      {option.label}
                    </option>
                  ))}
                </NativeSelect.Field>
                <NativeSelect.Indicator />
              </NativeSelect.Root>
            </Field>
          </Grid>

          <CampaignTypePreview control={control} />

          <Box mt={4}>
            <Controller
              control={control}
              name="audience"
              rules={{
                validate: (value) => {
                  if (!value || value.length === 0) {
                    return t("campaign.validation.selectAudience")
                  }

                  if (value.length > BRAND_INTELLIGENCE_LIMITS.audience) {
                    return t("campaign.validation.audienceLimit")
                  }

                  return true
                },
              }}
              render={({ field, fieldState }) => (
                <Field
                  required
                  invalid={!!fieldState.error}
                  errorText={fieldState.error?.message}
                  label={t("campaign.fields.audience")}
                  labelEndElement={renderFieldInfo(
                    t("campaign.fields.audience"),
                    t("campaign.fieldHelp.audience"),
                  )}
                  helperText={
                    fieldState.error
                      ? undefined
                      : t("campaign.helperText.audience")
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
          </Box>
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
                  {t("campaign.errors.reportFailedTitle")}
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
              {t("campaign.success.statusTitle")}
            </Text>
            <Text mt={1} color="ui.secondaryText">
              {submitSuccess}
            </Text>
          </Box>
        ) : null}

        <CampaignSubmitPanel
          control={control}
          invalidUsernames={invalidUsernames}
          isNotUsingCreators={isNotUsingCreators}
          isValidationPending={isValidationPending}
          isValidationStale={isValidationStale}
          missingUsernames={missingUsernames}
          normalizedProfiles={normalizedProfiles}
          orderedProfilesCount={orderedProfiles.length}
          reportIsPending={reportMutation.isPending}
        />
      </Flex>

      <CampaignStrategySummary
        control={control}
        expiredUsernames={expiredUsernames}
        isNotUsingCreators={isNotUsingCreators}
        normalizedProfiles={normalizedProfiles}
      />
    </Box>
  )
}

export default CampaignStrategyBuilder
