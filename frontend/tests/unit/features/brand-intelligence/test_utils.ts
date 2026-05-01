import { beforeEach, describe, expect, test, vi } from "vitest"
import type { ProfileExistenceItem } from "@/client"

import { OpenAPI } from "../../../../src/client"
import {
  BRAND_INTELLIGENCE_CAMPAIGN_ENDPOINT,
  BRAND_INTELLIGENCE_CREATOR_ENDPOINT,
  generateBrandIntelligenceReport,
} from "../../../../src/features/brand-intelligence/api"
import {
  buildProfileExistenceMap,
  isValidHttpUrl,
  normalizeListValues,
  normalizeUsernameList,
  orderProfileExistence,
} from "../../../../src/features/brand-intelligence/utils"

const createProfile = (
  overrides: Partial<ProfileExistenceItem> = {},
): ProfileExistenceItem => ({
  exists: true,
  expired: false,
  username: "creator_one",
  ...overrides,
})

const createResponse = ({
  body = new Blob(["report"], { type: "application/pdf" }),
  contentDisposition,
  contentType = "application/pdf",
  json,
  ok = true,
  status = 200,
}: {
  body?: Blob
  contentDisposition?: string
  contentType?: string
  json?: unknown
  ok?: boolean
  status?: number
}) =>
  ({
    blob: vi.fn().mockResolvedValue(body),
    headers: {
      get: vi.fn((name: string) => {
        if (name === "Content-Disposition") return contentDisposition ?? null
        if (name === "Content-Type") return contentType
        return null
      }),
    },
    json: vi.fn().mockResolvedValue(json),
    ok,
    status,
  }) as unknown as Response

describe("brand intelligence utils", () => {
  beforeEach(() => {
    vi.stubGlobal("fetch", vi.fn())
    localStorage.clear()
    localStorage.setItem("access_token", "token-123")
    OpenAPI.BASE = "https://api.test"
  })

  test("normalize_list_values_trims_filters_empty_and_dedupes", () => {
    // Arrange / Act
    const normalized = normalizeListValues([" Alpha ", "", "Alpha", "Beta "])

    // Assert
    expect(normalized).toEqual(["Alpha", "Beta"])
  })

  test("normalize_username_list_sanitizes_lowercases_and_dedupes", () => {
    // Arrange / Act
    const normalized = normalizeUsernameList([
      " @Creator.One ",
      "creator.one",
      "@Second_Creator",
      "",
    ])

    // Assert
    expect(normalized).toEqual(["creator.one", "second_creator"])
  })

  test("is_valid_http_url_accepts_only_http_and_https_urls", () => {
    // Arrange / Act / Assert
    expect(isValidHttpUrl("https://kiizama.com")).toBe(true)
    expect(isValidHttpUrl("http://kiizama.com")).toBe(true)
    expect(isValidHttpUrl("ftp://kiizama.com")).toBe(false)
    expect(isValidHttpUrl("not-a-url")).toBe(false)
    expect(isValidHttpUrl("")).toBe(false)
  })

  test("profile_existence_map_and_ordering_preserve_requested_shape", () => {
    // Arrange
    const profiles = [
      createProfile({ username: "ready" }),
      createProfile({ expired: true, username: "expired" }),
    ]

    // Act
    const profileMap = buildProfileExistenceMap(profiles)
    const orderedProfiles = orderProfileExistence(
      ["missing", "ready", "ready", "expired"],
      profiles,
    )

    // Assert
    expect(profileMap.get("ready")).toEqual(profiles[0])
    expect(orderedProfiles).toEqual([
      { exists: false, expired: false, username: "missing" },
      profiles[0],
      profiles[0],
      profiles[1],
    ])
  })

  test("brand_report_generation_uses_content_disposition_filename_and_pdf_metadata", async () => {
    // Arrange
    vi.mocked(fetch).mockResolvedValue(
      createResponse({
        contentDisposition: 'attachment; filename="custom-report.pdf"',
      }),
    )

    // Act
    const result = await generateBrandIntelligenceReport({
      endpointPath: BRAND_INTELLIGENCE_CAMPAIGN_ENDPOINT,
      fallbackFilename: "reputation_campaign_strategy.pdf",
      payload: {
        audience: ["Gen Z"],
        brand_context: "Context",
        brand_goals_context: "Goal",
        brand_goals_type: "Crisis",
        brand_name: "Kiizama Brand",
        campaign_type: "ugc_creators",
        profiles_list: [],
        timeframe: "3 months",
      },
    })

    // Assert
    expect(fetch).toHaveBeenCalledWith(
      "https://api.test/api/v1/brand-intelligence/reputation-campaign-strategy",
      expect.objectContaining({
        headers: expect.objectContaining({
          Accept: "application/pdf, application/zip",
          Authorization: "Bearer token-123",
        }),
        method: "POST",
      }),
    )
    expect(result.filename).toBe("custom-report.pdf")
    expect(result.contentType).toBe("application/pdf")
  })

  test("brand_report_generation_uses_slugged_fallback_for_zip_response", async () => {
    // Arrange
    vi.mocked(fetch).mockResolvedValue(
      createResponse({
        body: new Blob(["zip"], { type: "application/zip" }),
        contentType: "application/zip",
      }),
    )

    // Act
    const result = await generateBrandIntelligenceReport({
      endpointPath: BRAND_INTELLIGENCE_CREATOR_ENDPOINT,
      fallbackFilename: "reputation_creator_strategy.zip",
      payload: {
        audience: ["Gen Z"],
        creator_context: "Context",
        creator_username: "Creator One!",
        goal_context: "Goal",
        goal_type: "Community Trust",
        primary_platforms: ["Instagram"],
        timeframe: "6 months",
      },
    })

    // Assert
    expect(result.filename).toBe("reputation_creator_strategy_creator_one.zip")
    expect(result.contentType).toBe("application/zip")
  })

  test("brand_report_generation_error_detail_array_throws_first_message", async () => {
    // Arrange
    vi.mocked(fetch).mockResolvedValue(
      createResponse({
        json: { detail: [{ msg: "Invalid campaign payload." }] },
        ok: false,
        status: 422,
      }),
    )

    // Act / Assert
    await expect(
      generateBrandIntelligenceReport({
        endpointPath: BRAND_INTELLIGENCE_CAMPAIGN_ENDPOINT,
        fallbackFilename: "report.pdf",
        payload: {
          audience: [],
          brand_context: "",
          brand_goals_context: "",
          brand_goals_type: "",
          brand_name: "",
          campaign_type: "",
          profiles_list: [],
          timeframe: "",
        },
      }),
    ).rejects.toThrow("Invalid campaign payload.")
  })

  test("brand_report_generation_unauthorized_clears_token_and_redirects", async () => {
    // Arrange
    vi.mocked(fetch).mockResolvedValue(
      createResponse({ ok: false, status: 401 }),
    )
    const originalLocation = window.location
    Object.defineProperty(window, "location", {
      configurable: true,
      value: {
        href: "/",
      },
    })

    // Act / Assert
    try {
      await expect(
        generateBrandIntelligenceReport({
          endpointPath: BRAND_INTELLIGENCE_CREATOR_ENDPOINT,
          fallbackFilename: "report.pdf",
          payload: {
            audience: ["Gen Z"],
            creator_context: "Context",
            creator_username: "creator_one",
            goal_context: "Goal",
            goal_type: "Community Trust",
            primary_platforms: ["Instagram"],
            timeframe: "3 months",
          },
        }),
      ).rejects.toThrow("Your session has expired. Please log in again.")
      expect(localStorage.getItem("access_token")).toBeNull()
      expect(window.location.href).toBe("/login")
    } finally {
      Object.defineProperty(window, "location", {
        configurable: true,
        value: originalLocation,
      })
    }
  })
})
