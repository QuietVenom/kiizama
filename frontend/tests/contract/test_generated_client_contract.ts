import { describe, expect, test } from "vitest"
import type {
  AdminUserPublic,
  BillingNoticeCollectionPublic,
  BillingNoticePublic,
  BillingSessionPublic,
  BillingSummaryPublic,
  BrandIntelligenceGenerateReputationCampaignStrategyEndpointData,
  BrandIntelligenceGenerateReputationCreatorStrategyEndpointData,
  FeatureFlagPublic,
  FeatureFlagsPublic,
  InstagramBatchScrapeSummaryResponse,
  InstagramReportRequest,
  InstagramScrapeJobCreateResponse,
  InstagramScrapeJobStatusResponse,
  ProfileExistenceCollection,
  ReputationCampaignStrategyRequest,
  ReputationCreatorStrategyRequest,
  SocialMediaReportGenerateInstagramReportEndpointData,
  UserPublic,
  UsersUpdateUserAccessProfileData,
} from "../../src/client"
import {
  BillingService,
  BrandIntelligenceService,
  FeatureFlagsService,
  InstagramService,
  LoginService,
  OpenaiService,
  PublicFeatureFlagsService,
  SocialMediaReportService,
  UsersService,
} from "../../src/client"

describe("generated client contract", () => {
  test("generated_client_auth_and_users_services_expose_methods_consumed_by_frontend", () => {
    // Arrange / Act / Assert
    expect(LoginService.loginAccessToken).toBeTypeOf("function")
    expect(LoginService.recoverPassword).toBeTypeOf("function")
    expect(LoginService.resetPassword).toBeTypeOf("function")
    expect(UsersService.readUserMe).toBeTypeOf("function")
    expect(UsersService.updateUserMe).toBeTypeOf("function")
    expect(UsersService.updatePasswordMe).toBeTypeOf("function")
    expect(UsersService.registerUser).toBeTypeOf("function")
    expect(UsersService.readUsers).toBeTypeOf("function")
    expect(UsersService.createUser).toBeTypeOf("function")
    expect(UsersService.updateUser).toBeTypeOf("function")
    expect(UsersService.deleteUser).toBeTypeOf("function")
    expect(UsersService.updateUserAccessProfile).toBeTypeOf("function")
  })

  test("generated_client_business_services_expose_methods_consumed_by_frontend", () => {
    // Arrange / Act / Assert
    expect(BillingService.readBillingMe).toBeTypeOf("function")
    expect(BillingService.readBillingNotices).toBeTypeOf("function")
    expect(BillingService.createCheckoutSessionEndpoint).toBeTypeOf("function")
    expect(BillingService.createPortalSessionEndpoint).toBeTypeOf("function")
    expect(BillingService.markBillingNoticeRead).toBeTypeOf("function")
    expect(BillingService.dismissBillingNotice).toBeTypeOf("function")
    expect(FeatureFlagsService.listFeatureFlags).toBeTypeOf("function")
    expect(PublicFeatureFlagsService.getPublicFeatureFlag).toBeTypeOf(
      "function",
    )
    expect(PublicFeatureFlagsService.listPublicFeatureFlags).toBeTypeOf(
      "function",
    )
  })

  test("generated_client_ai_ig_and_report_services_expose_methods_consumed_by_frontend", () => {
    // Arrange / Act / Assert
    expect(InstagramService.createInstagramScrapeJob).toBeTypeOf("function")
    expect(InstagramService.createInstagramApifyScrapeJob).toBeTypeOf(
      "function",
    )
    expect(InstagramService.getInstagramScrapeJob).toBeTypeOf("function")
    expect(InstagramService.instagramScrapeProfilesBatch).toBeTypeOf("function")
    expect(InstagramService.instagramProfilesRecommendations).toBeTypeOf(
      "function",
    )
    expect(InstagramService.instagramScrapeProfilesApifyBatch).toBeTypeOf(
      "function",
    )
    expect(BrandIntelligenceService.readProfilesExistence).toBeTypeOf(
      "function",
    )
    expect(
      BrandIntelligenceService.generateReputationCampaignStrategyEndpoint,
    ).toBeTypeOf("function")
    expect(
      BrandIntelligenceService.generateReputationCreatorStrategyEndpoint,
    ).toBeTypeOf("function")
    expect(SocialMediaReportService.generateInstagramReportEndpoint).toBeTypeOf(
      "function",
    )
    expect(OpenaiService.runInstagramAi).toBeTypeOf("function")
  })

  test("generated_client_user_and_billing_shapes_keep_fields_consumed_by_ui", () => {
    // Arrange
    const user = {
      email: "owner@example.com",
      full_name: "Owner",
      id: "user-id",
      is_active: true,
      is_superuser: false,
    } satisfies UserPublic
    const adminUser = {
      ...user,
      access_profile: "ambassador",
      billing_eligible: true,
      managed_access_source: "admin",
      plan_status: "ambassador",
    } satisfies AdminUserPublic
    const billingNotice = {
      created_at: "2026-04-25T00:00:00Z",
      id: "notice-id",
      message: "Payment method required",
      notice_type: "subscription_paused",
      status: "unread",
      title: "Subscription paused",
    } satisfies BillingNoticePublic
    const billingSummary = {
      access_profile: "standard",
      billing_eligible: true,
      current_period_end: "2026-05-25",
      features: [
        {
          code: "reports",
          is_unlimited: false,
          limit: 10,
          name: "Reports",
          remaining: 7,
          reserved: 1,
          used: 2,
        },
      ],
      managed_access_source: null,
      notices: [billingNotice],
      plan_status: "base",
      renewal_day: "25",
      trial_eligible: false,
    } satisfies BillingSummaryPublic
    const notices = {
      data: [billingNotice],
    } satisfies BillingNoticeCollectionPublic
    const session = {
      url: "https://billing.example/session",
    } satisfies BillingSessionPublic

    // Act / Assert
    expect(adminUser).toMatchObject({
      access_profile: "ambassador",
      managed_access_source: "admin",
      plan_status: "ambassador",
    })
    expect(billingSummary.features[0]).toMatchObject({
      code: "reports",
      remaining: 7,
      reserved: 1,
      used: 2,
    })
    expect(notices.data[0]).toMatchObject({
      id: "notice-id",
      status: "unread",
    })
    expect(session.url).toContain("https://")
  })

  test("generated_client_feature_flag_and_scraper_shapes_keep_fields_consumed_by_ui", () => {
    // Arrange
    const flag = {
      description: "Enable public waiting list",
      is_enabled: true,
      is_public: true,
      key: "public.waiting_list",
    } satisfies FeatureFlagPublic
    const flags = { count: 1, data: [flag] } satisfies FeatureFlagsPublic
    const createdJob = {
      job_id: "job-id",
      status: "queued",
    } satisfies InstagramScrapeJobCreateResponse
    const jobStatus = {
      attempts: 1,
      created_at: "2026-04-25T00:00:00Z",
      error: null,
      execution_mode: "apify",
      expires_at: "2026-04-26T00:00:00Z",
      job_id: "job-id",
      references: {
        all_usernames: ["creator"],
        successful_usernames: ["creator"],
      },
      status: "done",
      summary: {
        counters: {
          failed: 0,
          not_found: 0,
          requested: 1,
          successful: 1,
        },
        usernames: [{ status: "success", username: "creator" }],
      },
      updated_at: "2026-04-25T00:01:00Z",
    } satisfies InstagramScrapeJobStatusResponse
    const summary =
      jobStatus.summary satisfies InstagramBatchScrapeSummaryResponse | null

    // Act / Assert
    expect(flags.data[0]).toMatchObject({
      is_enabled: true,
      is_public: true,
      key: "public.waiting_list",
    })
    expect(createdJob.status).toBe("queued")
    expect(jobStatus).toMatchObject({
      execution_mode: "apify",
      job_id: "job-id",
      status: "done",
    })
    expect(summary?.usernames?.[0]).toMatchObject({
      status: "success",
      username: "creator",
    })
  })

  test("generated_client_brand_and_report_request_shapes_keep_payload_fields_consumed_by_ui", () => {
    // Arrange
    const profilesExistence = {
      profiles: [
        { exists: true, expired: false, username: "creator" },
        { exists: false, expired: false, username: "missing" },
      ],
    } satisfies ProfileExistenceCollection
    const campaignRequest = {
      audience: ["Gen Z"],
      brand_context: "Lifestyle brand",
      brand_goals_context: "Launch campaign",
      brand_goals_type: "awareness",
      brand_name: "Kiizama",
      brand_urls: ["https://kiizama.example"],
      campaign_type: "nano",
      generate_html: true,
      generate_pdf: true,
      profiles_list: ["creator"],
      timeframe: "30 days",
    } satisfies ReputationCampaignStrategyRequest
    const creatorRequest = {
      audience: ["Marketing teams"],
      collaborators_list: ["brand"],
      creator_context: "Creator context",
      creator_username: "creator",
      creator_urls: ["https://instagram.com/creator"],
      generate_html: true,
      generate_pdf: false,
      goal_context: "Improve reputation",
      goal_type: "growth",
      primary_platforms: ["instagram"],
      reputation_signals: {
        concerns: ["low engagement"],
        strengths: ["trusted voice"],
      },
      timeframe: "quarter",
    } satisfies ReputationCreatorStrategyRequest
    const campaignEndpointData = {
      idempotencyKey: "idem-key",
      requestBody: campaignRequest,
    } satisfies BrandIntelligenceGenerateReputationCampaignStrategyEndpointData
    const creatorEndpointData = {
      idempotencyKey: "idem-key",
      requestBody: creatorRequest,
    } satisfies BrandIntelligenceGenerateReputationCreatorStrategyEndpointData
    const instagramReportRequest = {
      generate_html: true,
      generate_pdf: true,
      template_name: "instagram_report.html",
      usernames: ["creator"],
    } satisfies InstagramReportRequest
    const socialReportEndpointData = {
      idempotencyKey: "idem-key",
      requestBody: instagramReportRequest,
    } satisfies SocialMediaReportGenerateInstagramReportEndpointData
    const accessProfileData = {
      requestBody: { access_profile: "ambassador" },
      userId: "user-id",
    } satisfies UsersUpdateUserAccessProfileData

    // Act / Assert
    expect(profilesExistence.profiles?.[0]).toMatchObject({
      exists: true,
      expired: false,
      username: "creator",
    })
    expect(campaignEndpointData.requestBody).toMatchObject({
      brand_name: "Kiizama",
      profiles_list: ["creator"],
    })
    expect(creatorEndpointData.requestBody).toMatchObject({
      creator_username: "creator",
      primary_platforms: ["instagram"],
    })
    expect(socialReportEndpointData.requestBody).toMatchObject({
      template_name: "instagram_report.html",
      usernames: ["creator"],
    })
    expect(accessProfileData.requestBody.access_profile).toBe("ambassador")
  })
})
