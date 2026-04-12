import { Box } from "@chakra-ui/react"
import type { ReactNode } from "react"
import { IoMdInfinite } from "react-icons/io"
import type { BillingFeatureUsage, BillingSummary } from "./api"
import { formatBillingDateOnly } from "./date"

const planLabelMap = {
  admin: "Admin",
  ambassador: "Ambassador",
  base: "Base",
  none: "None",
  trial: "Trial",
} as const

export const hasManagedAccess = (summary?: BillingSummary) =>
  summary?.managed_access_source != null

export const hasUsablePlan = (summary?: BillingSummary) =>
  ["trial", "base"].includes(summary?.plan_status ?? "") &&
  summary?.access_revoked_reason == null

export const getBillingPlanLabel = (summary?: BillingSummary) => {
  if (summary?.managed_access_source === "admin") {
    return planLabelMap.admin
  }
  if (summary?.managed_access_source === "ambassador") {
    return planLabelMap.ambassador
  }
  return planLabelMap[summary?.plan_status ?? "none"]
}

export const renderFeatureUsageValue = (
  usage: BillingFeatureUsage | undefined,
): ReactNode => {
  if (!usage) {
    return "0 / 0"
  }
  if (usage.is_unlimited) {
    return (
      <Box as="span" display="inline-flex" alignItems="center" gap={1.5}>
        <Box as="span">{usage.used}</Box>
        <Box as="span">/</Box>
        <Box
          as="span"
          display="inline-flex"
          alignItems="center"
          aria-label="Unlimited"
        >
          <IoMdInfinite />
        </Box>
      </Box>
    )
  }
  return `${usage.remaining ?? 0} / ${usage.limit ?? 0}`
}

export const getBillingPeriodPresentation = (summary?: BillingSummary) => {
  if (summary?.managed_access_source != null) {
    return {
      label: "Usage Resets On",
      value:
        formatBillingDateOnly(summary.current_period_end) ?? "Not available",
      helper:
        "Access is managed internally. Usage resets at the start of each UTC month.",
    }
  }

  if (summary?.access_revoked_reason != null) {
    return {
      label: "Renewal Day",
      value: "Not available",
      helper: null,
    }
  }

  const hasScheduledCancellation =
    Boolean(summary?.cancel_at) &&
    ["active", "trialing"].includes(summary?.subscription_status ?? "")

  return {
    label: hasScheduledCancellation ? "Cancels On" : "Renewal Day",
    value: hasScheduledCancellation
      ? (formatBillingDateOnly(summary?.cancel_at) ?? "Not available")
      : summary?.renewal_day
        ? (formatBillingDateOnly(summary.renewal_day) ?? "Not available")
        : "Not available",
    helper: hasScheduledCancellation
      ? "Access remains available until the end of the current billing period."
      : null,
  }
}
