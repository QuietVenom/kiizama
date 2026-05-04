import { screen, waitFor } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import { useForm } from "react-hook-form"
import { beforeEach, describe, expect, test, vi } from "vitest"

import type { CampaignFormValues } from "../../../src/features/brand-intelligence/form-values"
import {
  buildCampaignStrategyPayload,
  campaignFormDefaultValues,
} from "../../../src/features/brand-intelligence/form-values"
import { renderWithProviders } from "../helpers/render"

const { billingApi, brandApi, localReports, reportFiles, toast } = vi.hoisted(
  () => ({
    billingApi: {
      invalidateBillingSummary: vi.fn(),
    },
    brandApi: {
      generateBrandIntelligenceReport: vi.fn(),
    },
    localReports: {
      saveLocalReport: vi.fn(),
    },
    reportFiles: {
      downloadBlob: vi.fn(),
    },
    toast: {
      showErrorToast: vi.fn(),
      showSuccessToast: vi.fn(),
    },
  }),
)

vi.mock("@/features/billing/api", () => ({
  invalidateBillingSummary: billingApi.invalidateBillingSummary,
}))

vi.mock("@/features/brand-intelligence/api", () => ({
  BRAND_INTELLIGENCE_CAMPAIGN_ENDPOINT:
    "/api/v1/brand-intelligence/reputation-campaign-strategy",
  generateBrandIntelligenceReport: brandApi.generateBrandIntelligenceReport,
}))

vi.mock("@/hooks/useCustomToast", () => ({
  default: () => toast,
}))

vi.mock("@/lib/local-reports", () => ({
  saveLocalReport: localReports.saveLocalReport,
}))

vi.mock("@/lib/report-files", () => ({
  downloadBlob: reportFiles.downloadBlob,
}))

const CampaignStrategyBuilder = (
  await import(
    "../../../src/components/BrandIntelligence/CampaignStrategyBuilder"
  )
).default

const createCampaignValues = (
  overrides: Partial<CampaignFormValues> = {},
): CampaignFormValues => ({
  ...campaignFormDefaultValues,
  audience: ["Gen Z"],
  brand_context: "Brand context",
  brand_goals_context: "Goal context",
  brand_goals_type: "Trust & Credibility Acceleration",
  brand_name: "Kiizama",
  brand_urls: ["https://kiizama.com"],
  campaign_type: "all_nano_seeding_ugc_flood",
  profiles_list: ["creator_one"],
  timeframe: "3 months",
  ...overrides,
})

const createValidation = ({
  missing = false,
  username = "creator_one",
}: {
  missing?: boolean
  username?: string
} = {}) => ({
  existingUsernames: missing ? [] : [username],
  expiredUsernames: [],
  hasValidatedProfiles: true,
  isValidationPending: false,
  isValidationStale: false,
  missingUsernames: missing ? [username] : [],
  orderedProfiles: [
    {
      exists: !missing,
      expired: false,
      username,
    },
  ],
  validateProfiles: vi.fn().mockResolvedValue({
    profiles: [
      {
        exists: !missing,
        expired: false,
        username,
      },
    ],
  }),
  validatedUsernames: [username],
  validationError: null,
})

const CampaignHarness = ({
  normalizedProfiles = ["creator_one"],
  validation = createValidation(),
  values = createCampaignValues(),
}: {
  normalizedProfiles?: string[]
  validation?: ReturnType<typeof createValidation>
  values?: CampaignFormValues
}) => {
  const form = useForm<CampaignFormValues>({
    defaultValues: values,
  })

  return (
    <CampaignStrategyBuilder
      form={form}
      normalizedProfiles={normalizedProfiles}
      validation={validation as never}
    />
  )
}

describe("campaign strategy builder", () => {
  beforeEach(() => {
    billingApi.invalidateBillingSummary.mockClear()
    brandApi.generateBrandIntelligenceReport.mockReset()
    localReports.saveLocalReport.mockReset()
    reportFiles.downloadBlob.mockClear()
    toast.showErrorToast.mockClear()
    toast.showSuccessToast.mockClear()
    localReports.saveLocalReport.mockResolvedValue(undefined)
    brandApi.generateBrandIntelligenceReport.mockResolvedValue({
      blob: new Blob(["pdf"], { type: "application/pdf" }),
      contentType: "application/pdf",
      filename: "campaign.pdf",
    })
  })

  test("campaign_strategy_required_fields_disable_submit_until_complete", () => {
    // Arrange / Act
    renderWithProviders(
      <CampaignHarness
        normalizedProfiles={[]}
        validation={createValidation({ missing: true })}
        values={campaignFormDefaultValues}
      />,
      { language: "en" },
    )

    // Assert
    expect(
      screen.getByText(/Add at least 1 creator username to unlock/i),
    ).toBeVisible()
    expect(
      screen.getByRole("button", { name: "Generate PDF report" }),
    ).toBeDisabled()
  })

  test("campaign_strategy_crisis_without_creators_submits_empty_profiles_payload", async () => {
    // Arrange
    const user = userEvent.setup()
    renderWithProviders(
      <CampaignHarness
        normalizedProfiles={[]}
        validation={createValidation({ username: "" })}
        values={createCampaignValues({ profiles_list: [] })}
      />,
      { language: "en" },
    )

    // Act
    await user.selectOptions(
      screen.getByRole("combobox", { name: /Brand goal/i }),
      "Crisis",
    )
    await user.click(
      screen.getByRole("checkbox", { name: "Not using creator(s)" }),
    )
    expect(await screen.findByText("Creator validation skipped")).toBeVisible()
    await user.click(
      screen.getByRole("button", { name: "Generate PDF report" }),
    )

    // Assert
    await waitFor(() => {
      expect(brandApi.generateBrandIntelligenceReport).toHaveBeenCalledWith(
        expect.objectContaining({
          payload: expect.objectContaining({
            brand_name: "Kiizama",
            profiles_list: [],
          }),
        }),
      )
    })
  })

  test("campaign_strategy_success_downloads_single_file_and_saves_local_report", async () => {
    // Arrange
    const user = userEvent.setup()
    renderWithProviders(<CampaignHarness />, { language: "en" })

    // Act
    await user.click(
      screen.getByRole("button", { name: "Generate PDF report" }),
    )

    // Assert
    await waitFor(() => {
      expect(brandApi.generateBrandIntelligenceReport).toHaveBeenCalledWith({
        endpointPath: "/api/v1/brand-intelligence/reputation-campaign-strategy",
        fallbackFilename: "reputation_campaign_strategy.pdf",
        payload: buildCampaignStrategyPayload(createCampaignValues(), {
          profilesList: ["creator_one"],
        }),
      })
      expect(reportFiles.downloadBlob).toHaveBeenCalledWith(
        expect.any(Blob),
        "campaign.pdf",
      )
      expect(localReports.saveLocalReport).toHaveBeenCalledWith(
        expect.objectContaining({
          filename: "campaign.pdf",
          reportType: "reputation-campaign-strategy",
          source: "brand-intelligence",
        }),
      )
    })
  })

  test("campaign_strategy_zip_response_uses_returned_filename", async () => {
    // Arrange
    const user = userEvent.setup()
    brandApi.generateBrandIntelligenceReport.mockResolvedValue({
      blob: new Blob(["zip"], { type: "application/zip" }),
      contentType: "application/zip",
      filename: "campaign.zip",
    })
    renderWithProviders(<CampaignHarness />, { language: "en" })

    // Act
    await user.click(
      screen.getByRole("button", { name: "Generate PDF report" }),
    )

    // Assert
    await waitFor(() => {
      expect(reportFiles.downloadBlob).toHaveBeenCalledWith(
        expect.any(Blob),
        "campaign.zip",
      )
    })
  })

  test("campaign_strategy_missing_profiles_blocks_submit_before_report_boundary", () => {
    // Arrange
    const validation = createValidation({ missing: true })
    renderWithProviders(<CampaignHarness validation={validation} />, {
      language: "en",
    })

    // Assert
    expect(
      screen.getByRole("button", { name: "Generate PDF report" }),
    ).toBeDisabled()
    expect(
      screen.getAllByText("Review the validated profiles and try again.")
        .length,
    ).toBeGreaterThan(0)
    expect(brandApi.generateBrandIntelligenceReport).not.toHaveBeenCalled()
  })

  test("campaign_strategy_api_error_renders_report_failure", async () => {
    // Arrange
    const user = userEvent.setup()
    brandApi.generateBrandIntelligenceReport.mockRejectedValue(
      new Error("OpenAI is unavailable."),
    )
    renderWithProviders(<CampaignHarness />, { language: "en" })

    // Act
    await user.click(
      screen.getByRole("button", { name: "Generate PDF report" }),
    )

    // Assert
    expect(await screen.findByText("Report generation failed")).toBeVisible()
    expect(screen.getByText("OpenAI is unavailable.")).toBeVisible()
  })
})
