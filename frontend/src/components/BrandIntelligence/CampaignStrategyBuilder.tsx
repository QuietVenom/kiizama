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
import { useMutation } from "@tanstack/react-query"
import { useEffect, useMemo, useState } from "react"
import {
  type Control,
  Controller,
  type FieldPath,
  type FieldValues,
  type UseFormReturn,
  useWatch,
} from "react-hook-form"
import { FiAlertCircle, FiFileText, FiSearch } from "react-icons/fi"

import UsernameTagsInput from "@/components/CreatorsSearch/UsernameTagsInput"
import { Button } from "@/components/ui/button"
import { Checkbox } from "@/components/ui/checkbox"
import { Field } from "@/components/ui/field"
import { TagsInputField } from "@/components/ui/tags-input-field"
import {
  BRAND_INTELLIGENCE_CAMPAIGN_ENDPOINT,
  generateBrandIntelligenceReport,
} from "@/features/brand-intelligence/api"
import {
  AUDIENCE_OPTIONS,
  BRAND_GOALS_TYPE_OPTIONS,
  CAMPAIGN_TYPE_OPTIONS,
  TIMEFRAME_OPTIONS,
} from "@/features/brand-intelligence/catalogs"
import {
  BRAND_INTELLIGENCE_LIMITS,
  CAMPAIGN_FIELD_HELP,
} from "@/features/brand-intelligence/form-config"
import type { CampaignFormValues } from "@/features/brand-intelligence/form-values"
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
  const campaignType = useWatch({ control, name: "campaign_type" })
  const selectedCampaignType = useMemo(
    () => CAMPAIGN_TYPE_OPTIONS.find((option) => option.name === campaignType),
    [campaignType],
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
        {selectedCampaignType.value}
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
    () => CAMPAIGN_TYPE_OPTIONS.find((option) => option.name === campaignType),
    [campaignType],
  )

  const summarySections = [
    {
      title: "Creators gate",
      items: [
        {
          label: "Creator usage",
          value: isNotUsingCreators
            ? "Not using creators for this campaign."
            : undefined,
        },
        {
          label: "Creator usernames",
          value: isNotUsingCreators ? [] : normalizedProfiles,
        },
        {
          label: "Expired profiles",
          value: isNotUsingCreators ? [] : expiredUsernames,
        },
      ],
    },
    {
      title: "Brand brief",
      items: [
        { label: "Brand name", value: brandName },
        { label: "Brand context", value: brandContext },
        { label: "Brand URLs", value: normalizedBrandUrls },
        { label: "Brand goal", value: brandGoalsType },
        { label: "Goal context", value: brandGoalsContext },
      ],
    },
    {
      title: "Campaign setup",
      items: [
        { label: "Audience", value: audience ?? [] },
        { label: "Timeframe", value: timeframe },
        {
          label: "Campaign type",
          value: selectedCampaignType?.title ?? campaignType,
        },
        {
          label: "Campaign type context",
          value: selectedCampaignType?.value,
        },
      ],
    },
  ]

  return (
    <StrategySummaryCard title="Campaign Strategy" sections={summarySections} />
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
      ? "Add at least 1 creator username to unlock the workflow."
      : !isNotUsingCreators && invalidUsernames.length > 0
        ? "Fix invalid usernames before continuing."
        : hasInvalidBrandUrls
          ? "Use valid http or https URLs."
          : !hasRequiredFields
            ? "Complete the required fields to enable report generation."
            : !isNotUsingCreators && isValidationPending
              ? "Profile validation is still running."
              : !isNotUsingCreators &&
                  (isValidationStale || orderedProfilesCount === 0)
                ? "Validate profiles before generating the report."
                : !isNotUsingCreators && missingUsernames.length > 0
                  ? "consulte los perfiles validados y vuelva a intentar"
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
            Generate campaign strategy PDF
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

const CampaignStrategyBuilder = ({
  form,
  normalizedProfiles,
  validation,
}: CampaignStrategyBuilderProps) => {
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
          throw new Error("consulte los perfiles validados y vuelva a intentar")
        }
      }

      return generateBrandIntelligenceReport({
        endpointPath: BRAND_INTELLIGENCE_CAMPAIGN_ENDPOINT,
        fallbackFilename: "reputation_campaign_strategy.pdf",
        payload: {
          ...values,
          audience: values.audience,
          brand_context: values.brand_context.trim(),
          brand_goals_context: values.brand_goals_context.trim(),
          brand_name: values.brand_name.trim(),
          brand_urls: normalizeListValues(values.brand_urls ?? []),
          campaign_type: values.campaign_type,
          generate_html: false,
          generate_pdf: true,
          profiles_list: profilesList,
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
          reportType: "reputation-campaign-strategy",
          source: "brand-intelligence",
        })
        showSuccessToast("Campaign strategy PDF downloaded and saved locally.")
      } catch {
        showErrorToast(
          "Campaign strategy PDF downloaded, but it could not be saved locally.",
        )
      }
    },
    onError: (error) => {
      setSubmitError(
        extractApiErrorMessage(error, "Unable to generate the report."),
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
          eyebrow="Step 1"
          title="Set the brand goal and creators"
          description="Choose the brand goal first. If this is a Crisis campaign, you can explicitly decide not to use creators; otherwise, add creator usernames to unlock the rest of the campaign strategy form."
        >
          <Field
            required
            invalid={!!errors.brand_goals_type}
            errorText={errors.brand_goals_type?.message}
            label="Brand goal"
            labelEndElement={renderFieldInfo(
              "Brand goal",
              CAMPAIGN_FIELD_HELP.brand_goals_type,
            )}
          >
            <NativeSelect.Root>
              <NativeSelect.Field
                {...register("brand_goals_type", {
                  required: "Select the primary brand goal.",
                })}
                {...autofillIgnoreProps}
                {...inputStyles}
              >
                <option value="">Select a goal</option>
                {BRAND_GOALS_TYPE_OPTIONS.map((option) => (
                  <option key={option} value={option}>
                    {option}
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
                  return "Add at least 1 creator username."
                }

                if (value.length > BRAND_INTELLIGENCE_LIMITS.campaignProfiles) {
                  return "You can include up to 15 creator usernames."
                }

                if (
                  value.some((username) => !isValidInstagramUsername(username))
                ) {
                  return "Use lowercase letters, numbers, periods or underscores, up to 30 characters."
                }

                return true
              },
            }}
            render={({ field, fieldState }) => (
              <Field
                required={!isNotUsingCreators}
                invalid={!!fieldState.error}
                errorText={fieldState.error?.message}
                label="Creator usernames"
                labelEndElement={renderFieldInfo(
                  "Creator usernames",
                  CAMPAIGN_FIELD_HELP.profiles_list,
                )}
                helperText={
                  fieldState.error
                    ? undefined
                    : isNotUsingCreators
                      ? "Creators are disabled for this Crisis campaign while this option is active."
                      : "Paste a list, press Enter, or separate usernames with commas."
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
                  placeholder="creator_one, creator.two, another_creator"
                  value={field.value}
                />
              </Field>
            )}
          />

          <Field
            mt={4}
            helperText={
              isCrisisGoal
                ? "Available for Crisis campaigns. When enabled, the report will be generated without creator usernames or profile validation."
                : "Select Brand goal = Crisis to enable this option."
            }
          >
            <Checkbox
              checked={notUsingCreators}
              disabled={!isCrisisGoal}
              onCheckedChange={({ checked }) =>
                setNotUsingCreators(Boolean(checked))
              }
            >
              Not using creator(s)
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
                  Creators not required for Crisis
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
                  {normalizedProfiles.length} /{" "}
                  {BRAND_INTELLIGENCE_LIMITS.campaignProfiles} creator usernames
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
                  Workflow unlocked
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
                Validate profiles
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
                  Creator validation skipped
                </Text>
                <Text mt={2} color="ui.secondaryText">
                  This Crisis campaign is set to not use creators, so creator
                  username validation is not required and the report will be
                  generated with an empty creators list.
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
          eyebrow="Step 2"
          title="Brand brief"
          description="Capture the brand context and supporting inputs that will guide the strategy recommendation."
        >
          <Field
            required
            invalid={!!errors.brand_name}
            errorText={errors.brand_name?.message}
            label="Brand name"
            labelEndElement={renderFieldInfo(
              "Brand name",
              CAMPAIGN_FIELD_HELP.brand_name,
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
                required: "Brand name is required.",
                maxLength: {
                  value: 120,
                  message: "Use 120 characters or less.",
                },
              })}
              {...autofillIgnoreProps}
              {...inputStyles}
              disabled={!isWorkflowUnlocked}
              maxLength={120}
              placeholder="Acme Skincare"
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
              label="Brand context"
              labelEndElement={renderFieldInfo(
                "Brand context",
                CAMPAIGN_FIELD_HELP.brand_context,
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
                  required: "Brand context is required.",
                  maxLength: {
                    value: 500,
                    message: "Use 500 characters or less.",
                  },
                })}
                {...autofillIgnoreProps}
                {...inputStyles}
                disabled={!isWorkflowUnlocked}
                maxLength={500}
                minH="132px"
                placeholder="Share the current business context, positioning, and what is happening around the brand."
              />
            </Field>

            <Field
              required
              invalid={!!errors.brand_goals_context}
              errorText={errors.brand_goals_context?.message}
              label="Goal context"
              labelEndElement={renderFieldInfo(
                "Goal context",
                CAMPAIGN_FIELD_HELP.brand_goals_context,
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
                  required: "Goal context is required.",
                  maxLength: {
                    value: 500,
                    message: "Use 500 characters or less.",
                  },
                })}
                {...autofillIgnoreProps}
                {...inputStyles}
                disabled={!isWorkflowUnlocked}
                maxLength={500}
                minH="132px"
                placeholder="Add context for the goal so the recommendation can weigh the right tradeoffs."
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
                    return "Add up to 3 brand URLs."
                  }

                  if ((value ?? []).some((url) => !isValidHttpUrl(url))) {
                    return "Use valid http or https URLs."
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
                    label="Brand URLs"
                    labelEndElement={renderFieldInfo(
                      "Brand URLs",
                      CAMPAIGN_FIELD_HELP.brand_urls,
                    )}
                    helperText={
                      fieldState.error
                        ? undefined
                        : "Optional. Add up to 3 relevant URLs for the brand."
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
                      placeholder="https://brand.com, https://instagram.com/brand"
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
          title="Campaign strategy setup"
          description="Choose the audience, timeframe, and campaign model that best match the report you want to generate."
        >
          <Grid templateColumns={{ base: "1fr", lg: "repeat(2, 1fr)" }} gap={4}>
            <Field
              required
              invalid={!!errors.timeframe}
              errorText={errors.timeframe?.message}
              label="Timeframe"
              labelEndElement={renderFieldInfo(
                "Timeframe",
                CAMPAIGN_FIELD_HELP.timeframe,
              )}
            >
              <NativeSelect.Root disabled={!isWorkflowUnlocked}>
                <NativeSelect.Field
                  {...register("timeframe", {
                    required: "Select the timeframe.",
                  })}
                  {...autofillIgnoreProps}
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

            <Field
              required
              invalid={!!errors.campaign_type}
              errorText={errors.campaign_type?.message}
              label="Campaign type"
              labelEndElement={renderFieldInfo(
                "Campaign type",
                CAMPAIGN_FIELD_HELP.campaign_type,
              )}
            >
              <NativeSelect.Root disabled={!isWorkflowUnlocked}>
                <NativeSelect.Field
                  {...register("campaign_type", {
                    required: "Select the campaign type.",
                  })}
                  {...autofillIgnoreProps}
                  {...inputStyles}
                >
                  <option value="">Select a campaign model</option>
                  {CAMPAIGN_TYPE_OPTIONS.map((option) => (
                    <option key={option.name} value={option.name}>
                      {option.title}
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
                    CAMPAIGN_FIELD_HELP.audience,
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
              Campaign report generated
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
