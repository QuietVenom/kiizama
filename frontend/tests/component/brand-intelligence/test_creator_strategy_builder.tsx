import { screen, waitFor } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import { useState } from "react"
import { useForm } from "react-hook-form"
import { beforeEach, describe, expect, test, vi } from "vitest"

import {
  buildCreatorStrategyPayload,
  type CreatorFormValues,
  type CreatorTextInputValues,
  creatorFormDefaultValues,
  creatorTextInputDefaultValues,
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
  BRAND_INTELLIGENCE_CREATOR_ENDPOINT:
    "/api/v1/brand-intelligence/reputation-creator-strategy",
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

const CreatorStrategyBuilder = (
  await import(
    "../../../src/components/BrandIntelligence/CreatorStrategyBuilder"
  )
).default

const createCreatorValues = (
  overrides: Partial<CreatorFormValues> = {},
): CreatorFormValues => ({
  ...creatorFormDefaultValues,
  audience: ["Gen Z"],
  collaborators_list: ["Brand One", "Brand One"],
  creator_context: "Creator context",
  creator_urls: ["https://creator.test"],
  creator_username: "creator_one",
  goal_context: "Goal context",
  goal_type: "Community Trust",
  primary_platforms: ["Instagram", "TikTok", "Instagram"],
  reputation_signals: {
    concerns: ["Fatigue", ""],
    incidents: ["Backlash"],
    strengths: ["Trust", "Trust"],
    weaknesses: [],
  },
  timeframe: "6 months",
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

const CreatorHarness = ({
  creatorTextInputValues = creatorTextInputDefaultValues,
  creatorUsername = "creator_one",
  creatorValidationUsernames = ["creator_one"],
  validation = createValidation(),
  values = createCreatorValues(),
}: {
  creatorTextInputValues?: CreatorTextInputValues
  creatorUsername?: string
  creatorValidationUsernames?: string[]
  validation?: ReturnType<typeof createValidation>
  values?: CreatorFormValues
}) => {
  const form = useForm<CreatorFormValues>({
    defaultValues: values,
  })
  const [textInputValues, setTextInputValues] = useState(creatorTextInputValues)

  return (
    <CreatorStrategyBuilder
      creatorTextInputValues={textInputValues}
      creatorUsername={creatorUsername}
      creatorValidationUsernames={creatorValidationUsernames}
      form={form}
      onTextInputValuesChange={setTextInputValues}
      validation={validation as never}
    />
  )
}

describe("creator strategy builder", () => {
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
      filename: "creator.pdf",
    })
  })

  test("creator_strategy_missing_username_disables_submit", () => {
    // Arrange / Act
    renderWithProviders(
      <CreatorHarness
        creatorUsername=""
        creatorValidationUsernames={[]}
        validation={createValidation({ username: "" })}
        values={creatorFormDefaultValues}
      />,
    )

    // Assert
    expect(
      screen.getByText("Add the creator username to unlock the workflow."),
    ).toBeVisible()
    expect(
      screen.getByRole("button", { name: "Generate PDF report" }),
    ).toBeDisabled()
  })

  test("creator_strategy_success_submits_normalized_payload_and_downloads_file", async () => {
    // Arrange
    const user = userEvent.setup()
    const values = createCreatorValues()
    renderWithProviders(<CreatorHarness values={values} />)

    // Act
    await user.click(
      screen.getByRole("button", { name: "Generate PDF report" }),
    )

    // Assert
    await waitFor(() => {
      expect(brandApi.generateBrandIntelligenceReport).toHaveBeenCalledWith({
        endpointPath: "/api/v1/brand-intelligence/reputation-creator-strategy",
        fallbackFilename: "reputation_creator_strategy.pdf",
        payload: buildCreatorStrategyPayload(values),
      })
      expect(reportFiles.downloadBlob).toHaveBeenCalledWith(
        expect.any(Blob),
        "creator.pdf",
      )
      expect(localReports.saveLocalReport).toHaveBeenCalledWith(
        expect.objectContaining({
          filename: "creator.pdf",
          reportType: "reputation-creator-strategy",
          source: "brand-intelligence",
        }),
      )
    })
  })

  test("creator_strategy_zip_response_uses_returned_filename", async () => {
    // Arrange
    const user = userEvent.setup()
    brandApi.generateBrandIntelligenceReport.mockResolvedValue({
      blob: new Blob(["zip"], { type: "application/zip" }),
      contentType: "application/zip",
      filename: "creator.zip",
    })
    renderWithProviders(<CreatorHarness />)

    // Act
    await user.click(
      screen.getByRole("button", { name: "Generate PDF report" }),
    )

    // Assert
    await waitFor(() => {
      expect(reportFiles.downloadBlob).toHaveBeenCalledWith(
        expect.any(Blob),
        "creator.zip",
      )
    })
  })

  test("creator_strategy_missing_profile_blocks_submit_before_report_boundary", () => {
    // Arrange
    const validation = createValidation({ missing: true })
    renderWithProviders(<CreatorHarness validation={validation} />)

    // Assert
    expect(
      screen.getByRole("button", { name: "Generate PDF report" }),
    ).toBeDisabled()
    expect(
      screen.getAllByText("consulte los perfiles validados y vuelva a intentar")
        .length,
    ).toBeGreaterThan(0)
    expect(brandApi.generateBrandIntelligenceReport).not.toHaveBeenCalled()
  })

  test("creator_strategy_api_error_renders_report_failure", async () => {
    // Arrange
    const user = userEvent.setup()
    brandApi.generateBrandIntelligenceReport.mockRejectedValue(
      new Error("OpenAI is unavailable."),
    )
    renderWithProviders(<CreatorHarness />)

    // Act
    await user.click(
      screen.getByRole("button", { name: "Generate PDF report" }),
    )

    // Assert
    expect(await screen.findByText("Report generation failed")).toBeVisible()
    expect(screen.getByText("OpenAI is unavailable.")).toBeVisible()
  })
})
