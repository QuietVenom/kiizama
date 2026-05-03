import { screen } from "@testing-library/react"
import { createElement, Fragment } from "react"
import { describe, expect, test } from "vitest"

import type {
  BillingFeatureUsage,
  BillingSummary,
} from "../../../../src/features/billing/api"
import {
  getBillingPeriodPresentation,
  getBillingPlanLabel,
  hasManagedAccess,
  hasUsablePlan,
  renderFeatureUsageValue,
} from "../../../../src/features/billing/presentation"
import { renderWithProviders } from "../../../component/helpers/render"

const createBillingSummary = (
  overrides: Partial<BillingSummary> = {},
): BillingSummary => ({
  access_profile: "standard",
  access_revoked_reason: null,
  billing_eligible: true,
  cancel_at: null,
  current_period_end: null,
  current_period_start: null,
  features: [],
  latest_invoice_status: null,
  managed_access_source: null,
  pending_ambassador_activation: false,
  plan_status: "none",
  renewal_day: null,
  subscription_status: null,
  trial_eligible: true,
  notices: [],
  ...overrides,
})

const createFeatureUsage = (
  overrides: Partial<BillingFeatureUsage> = {},
): BillingFeatureUsage => ({
  code: "ig_scraper",
  is_unlimited: false,
  limit: 10,
  name: "Profiles",
  remaining: 7,
  reserved: 1,
  used: 2,
  ...overrides,
})

describe("billing presentation", () => {
  test.each([
    ["none", createBillingSummary({ plan_status: "none" }), "None"],
    ["trial", createBillingSummary({ plan_status: "trial" }), "Trial"],
    ["base", createBillingSummary({ plan_status: "base" }), "Base"],
    [
      "ambassador",
      createBillingSummary({ plan_status: "ambassador" }),
      "Ambassador",
    ],
    [
      "managed admin",
      createBillingSummary({
        managed_access_source: "admin",
        plan_status: "base",
      }),
      "Admin",
    ],
    [
      "managed ambassador",
      createBillingSummary({
        managed_access_source: "ambassador",
        plan_status: "base",
      }),
      "Ambassador",
    ],
  ])(
    "billing_plan_label_%s_summary_returns_expected_label",
    (_scenario, summary, expected) => {
      // Arrange / Act / Assert
      expect(getBillingPlanLabel(summary)).toBe(expected)
    },
  )

  test("billing_plan_label_missing_summary_returns_none", () => {
    // Arrange / Act / Assert
    expect(getBillingPlanLabel()).toBe("None")
  })

  test("billing_access_managed_source_reports_managed_access", () => {
    // Arrange
    const managedSummary = createBillingSummary({
      managed_access_source: "admin",
    })
    const standardSummary = createBillingSummary()

    // Act / Assert
    expect(hasManagedAccess(managedSummary)).toBe(true)
    expect(hasManagedAccess(standardSummary)).toBe(false)
  })

  test.each([
    ["trial", createBillingSummary({ plan_status: "trial" }), true],
    ["base", createBillingSummary({ plan_status: "base" }), true],
    [
      "revoked base",
      createBillingSummary({
        access_revoked_reason: "payment_failed",
        plan_status: "base",
      }),
      false,
    ],
    ["ambassador", createBillingSummary({ plan_status: "ambassador" }), false],
    [
      "past due status without revocation",
      createBillingSummary({
        plan_status: "base",
        subscription_status: "past_due",
      }),
      true,
    ],
  ])(
    "billing_usable_plan_%s_returns_expected_result",
    (_scenario, summary, expected) => {
      // Arrange / Act / Assert
      expect(hasUsablePlan(summary)).toBe(expected)
    },
  )

  test("billing_period_managed_access_returns_usage_reset_copy", () => {
    // Arrange
    const summary = createBillingSummary({
      current_period_end: "2026-01-31",
      managed_access_source: "admin",
    })

    // Act
    const result = getBillingPeriodPresentation(summary, { language: "es" })

    // Assert
    expect(result.label).toBe("Usage Resets On")
    expect(result.value).toContain("2026")
    expect(result.helper).toContain("Access is managed internally")
  })

  test("billing_period_scheduled_cancellation_returns_cancel_copy", () => {
    // Arrange
    const summary = createBillingSummary({
      cancel_at: "2026-02-15",
      subscription_status: "active",
    })

    // Act
    const result = getBillingPeriodPresentation(summary, { language: "es" })

    // Assert
    expect(result.label).toBe("Cancels On")
    expect(result.value).toContain("2026")
    expect(result.helper).toBe(
      "Access remains available until the end of the current billing period.",
    )
  })

  test("billing_period_revoked_access_returns_not_available", () => {
    // Arrange
    const summary = createBillingSummary({
      access_revoked_reason: "payment_failed",
      renewal_day: "2026-03-01",
    })

    // Act
    const result = getBillingPeriodPresentation(summary, { language: "es" })

    // Assert
    expect(result).toEqual({
      helper: null,
      label: "Renewal Day",
      value: "Not available",
    })
  })

  test("billing_period_missing_renewal_date_returns_not_available", () => {
    // Arrange / Act
    const result = getBillingPeriodPresentation(createBillingSummary(), {
      language: "es",
    })

    // Assert
    expect(result).toEqual({
      helper: null,
      label: "Renewal Day",
      value: "Not available",
    })
  })

  test("billing_feature_usage_missing_usage_renders_zero_over_zero", () => {
    // Arrange
    renderWithProviders(
      createElement(Fragment, null, renderFeatureUsageValue(undefined)),
    )

    // Act / Assert
    expect(screen.getByText("0 / 0")).toBeVisible()
  })

  test("billing_feature_usage_limited_usage_renders_remaining_over_limit", () => {
    // Arrange
    renderWithProviders(
      createElement(
        Fragment,
        null,
        renderFeatureUsageValue(createFeatureUsage()),
      ),
    )

    // Act / Assert
    expect(screen.getByText("7 / 10")).toBeVisible()
  })

  test("billing_feature_usage_unlimited_usage_renders_accessible_infinite_label", () => {
    // Arrange
    renderWithProviders(
      createElement(
        Fragment,
        null,
        renderFeatureUsageValue(
          createFeatureUsage({
            is_unlimited: true,
            limit: null,
            remaining: null,
            used: 42,
          }),
        ),
      ),
    )

    // Act / Assert
    expect(screen.getByText("42")).toBeVisible()
    expect(screen.getByLabelText("Unlimited")).toBeVisible()
  })
})
