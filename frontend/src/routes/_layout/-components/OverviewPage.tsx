import { Box, Button, Flex, Grid, Text } from "@chakra-ui/react"
import { useQuery } from "@tanstack/react-query"
import { useNavigate } from "@tanstack/react-router"
import { useTranslation } from "react-i18next"
import { FiFileText, FiShield, FiUserCheck } from "react-icons/fi"

import DashboardPageShell from "@/components/Dashboard/DashboardPageShell"
import MetricCard from "@/components/Dashboard/MetricCard"
import RecentReportsCard from "@/components/Dashboard/RecentReportsCard"
import StrategicInsightCard from "@/components/Dashboard/StrategicInsightCard"
import {
  billingSummaryQueryOptions,
  getFeatureUsage,
} from "@/features/billing/api"
import {
  getBillingPeriodPresentation,
  getBillingPlanLabel,
  hasManagedAccess,
  hasUsablePlan,
  renderFeatureUsageValue,
} from "@/features/billing/presentation"
import useAuth from "@/hooks/useAuth"

export function OverviewPage() {
  const { i18n, t } = useTranslation("dashboard")
  const { t: tBilling } = useTranslation("billing")
  const { user: currentUser } = useAuth()
  const navigate = useNavigate()
  const displayName =
    currentUser?.full_name || currentUser?.email || t("overview.fallbackName")
  const { data: billing } = useQuery(billingSummaryQueryOptions)

  const profilesUsage = getFeatureUsage(billing, "ig_scraper")
  const reportsUsage = getFeatureUsage(billing, "social_media_report")
  const reputationUsage = getFeatureUsage(billing, "reputation_strategy")
  const isManagedAccess = hasManagedAccess(billing)
  const planLabel = getBillingPlanLabel(billing, (key) => tBilling(key))
  const periodPresentation = getBillingPeriodPresentation(billing, {
    language: i18n.resolvedLanguage ?? i18n.language,
    t: (key) => tBilling(key),
  })
  const hasActivePlan = hasUsablePlan(billing)
  const paymentsCtaLabel = hasActivePlan
    ? t("overview.paymentsCta")
    : t("overview.activateSubscription")

  return (
    <DashboardPageShell>
      <Box>
        <Flex
          mb={{ base: 7, lg: 8 }}
          gap={4}
          align={{ base: "flex-start", lg: "flex-start" }}
          justify="space-between"
          direction={{ base: "column", lg: "row" }}
        >
          <Box>
            <Text
              fontSize={{ base: "2xl", md: "3xl", lg: "4xl" }}
              fontWeight="black"
              letterSpacing="-0.03em"
              lineHeight="1.05"
              truncate
              maxW="32ch"
            >
              {t("overview.greeting", { name: displayName })} 👋
            </Text>
            <Text
              mt={3}
              color="ui.secondaryText"
              fontSize={{ base: "md", lg: "lg" }}
              fontWeight="medium"
              maxW="50ch"
            >
              {t("overview.subtitle")}
            </Text>
          </Box>
          {isManagedAccess ? null : (
            <Button
              alignSelf={{ base: "stretch", lg: "flex-start" }}
              layerStyle={hasActivePlan ? undefined : "brandGradientButton"}
              variant={hasActivePlan ? "outline" : undefined}
              onClick={() =>
                navigate({
                  to: "/settings",
                  search: { tab: "payments" },
                })
              }
            >
              {paymentsCtaLabel}
            </Button>
          )}
        </Flex>

        <Grid
          templateColumns={{
            base: "1fr",
            md: "repeat(2, 1fr)",
            xl: "repeat(3, 1fr)",
          }}
          gap={5}
          mb={{ base: 7, lg: 8 }}
        >
          <MetricCard
            icon={FiUserCheck}
            label={t("overview.metrics.profiles")}
            value={renderFeatureUsageValue(
              profilesUsage,
              tBilling("usage.unlimited"),
            )}
            tone="info"
          />
          <MetricCard
            icon={FiFileText}
            label={t("overview.metrics.socialMediaReports")}
            value={renderFeatureUsageValue(
              reportsUsage,
              tBilling("usage.unlimited"),
            )}
            tone="accent"
          />
          <MetricCard
            icon={FiShield}
            label={t("overview.metrics.reputationStrategy")}
            value={renderFeatureUsageValue(
              reputationUsage,
              tBilling("usage.unlimited"),
            )}
            tone="positive"
          />
        </Grid>

        <Grid templateColumns={{ base: "1fr", xl: "1.6fr 1fr" }} gap={6}>
          <Box minW={0}>
            <RecentReportsCard />
          </Box>
          <Box minW={0}>
            <StrategicInsightCard
              planLabel={planLabel}
              periodLabel={periodPresentation.label}
              periodValue={periodPresentation.value}
            />
          </Box>
        </Grid>
      </Box>
    </DashboardPageShell>
  )
}
