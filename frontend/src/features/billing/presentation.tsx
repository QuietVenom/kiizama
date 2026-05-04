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

type BillingT = (key: string) => string

export const hasManagedAccess = (summary?: BillingSummary) =>
  summary?.managed_access_source != null

export const hasUsablePlan = (summary?: BillingSummary) =>
  ["trial", "base"].includes(summary?.plan_status ?? "") &&
  summary?.access_revoked_reason == null

export const getBillingPlanLabel = (summary?: BillingSummary, t?: BillingT) => {
  const translatePlan = (plan: keyof typeof planLabelMap) =>
    t ? t(`plan.${plan}`) : planLabelMap[plan]

  if (summary?.managed_access_source === "admin") {
    return translatePlan("admin")
  }
  if (summary?.managed_access_source === "ambassador") {
    return translatePlan("ambassador")
  }
  return translatePlan(
    (summary?.plan_status ?? "none") as keyof typeof planLabelMap,
  )
}

export const renderFeatureUsageValue = (
  usage: BillingFeatureUsage | undefined,
  unlimitedLabel = "Unlimited",
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
          aria-label={unlimitedLabel}
        >
          <IoMdInfinite />
        </Box>
      </Box>
    )
  }
  return `${usage.remaining ?? 0} / ${usage.limit ?? 0}`
}

export const getBillingPeriodPresentation = (
  summary?: BillingSummary,
  options?: {
    language?: string | null
    t?: BillingT
  },
) => {
  const t =
    options?.t ??
    ((key: string) => {
      const defaults: Record<string, string> = {
        "period.usageResetsOn": "Usage Resets On",
        "period.renewalDay": "Renewal Day",
        "period.cancelsOn": "Cancels On",
        "period.notAvailable": "Not available",
        "period.managedHelper":
          "Access is managed internally. Usage resets at the start of each UTC month.",
        "period.cancellationHelper":
          "Access remains available until the end of the current billing period.",
      }
      return defaults[key] ?? key
    })

  if (summary?.managed_access_source != null) {
    return {
      label: t("period.usageResetsOn"),
      value:
        formatBillingDateOnly(summary.current_period_end, options?.language) ??
        t("period.notAvailable"),
      helper: t("period.managedHelper"),
    }
  }

  if (summary?.access_revoked_reason != null) {
    return {
      label: t("period.renewalDay"),
      value: t("period.notAvailable"),
      helper: null,
    }
  }

  const hasScheduledCancellation =
    Boolean(summary?.cancel_at) &&
    ["active", "trialing"].includes(summary?.subscription_status ?? "")

  return {
    label: hasScheduledCancellation
      ? t("period.cancelsOn")
      : t("period.renewalDay"),
    value: hasScheduledCancellation
      ? (formatBillingDateOnly(summary?.cancel_at, options?.language) ??
        t("period.notAvailable"))
      : summary?.renewal_day
        ? (formatBillingDateOnly(summary.renewal_day, options?.language) ??
          t("period.notAvailable"))
        : t("period.notAvailable"),
    helper: hasScheduledCancellation ? t("period.cancellationHelper") : null,
  }
}
