import {
  Badge,
  Box,
  Button,
  Container,
  Flex,
  Grid,
  Heading,
  Text,
} from "@chakra-ui/react"
import { useMutation, useQuery } from "@tanstack/react-query"
import {
  billingSummaryQueryOptions,
  createCheckoutSession,
  createPortalSession,
  getFeatureUsage,
} from "@/features/billing/api"
import {
  getBillingPeriodPresentation,
  getBillingPlanLabel,
  hasManagedAccess,
  renderFeatureUsageValue,
} from "@/features/billing/presentation"
import useCustomToast from "@/hooks/useCustomToast"

const subscriptionLabelMap: Record<string, string> = {
  active: "Active",
  canceled: "Canceled",
  incomplete: "Incomplete",
  incomplete_expired: "Incomplete expired",
  past_due: "Past due",
  paused: "Paused",
  trialing: "Trialing",
  unpaid: "Unpaid",
}

const subscriptionToneMap: Record<string, "gray" | "green" | "orange" | "red"> =
  {
    active: "green",
    canceled: "gray",
    incomplete: "orange",
    incomplete_expired: "gray",
    past_due: "orange",
    paused: "orange",
    trialing: "green",
    unpaid: "red",
  }

const noticeToneMap = {
  access_revoked: "red",
  invoice_upcoming: "orange",
  subscription_paused: "orange",
  trial_will_end: "yellow",
} as const

const Payments = () => {
  const { showErrorToast } = useCustomToast()
  const { data, isLoading } = useQuery(billingSummaryQueryOptions)

  const checkoutMutation = useMutation({
    mutationFn: createCheckoutSession,
    onSuccess: ({ url }) => {
      window.location.assign(url)
    },
    onError: (error) => {
      showErrorToast(
        error instanceof Error ? error.message : "Unable to start checkout.",
      )
    },
  })

  const portalMutation = useMutation({
    mutationFn: createPortalSession,
    onSuccess: ({ url }) => {
      window.location.assign(url)
    },
    onError: (error) => {
      showErrorToast(
        error instanceof Error
          ? error.message
          : "Unable to open billing management.",
      )
    },
  })

  const showCheckoutCta =
    data?.billing_eligible &&
    !hasManagedAccess(data) &&
    data.access_profile === "standard" &&
    (data.subscription_status == null ||
      ["canceled", "incomplete_expired"].includes(data.subscription_status))

  const checkoutLabel = data?.trial_eligible ? "Start Trial" : "Start Base Plan"
  const isManagedAccess = hasManagedAccess(data)
  const periodPresentation = getBillingPeriodPresentation(data)
  const portalLabel =
    data?.subscription_status === "paused"
      ? "Add Payment Method"
      : "Manage Billing"

  const featureCards = [
    {
      label: "Profiles",
      value: getFeatureUsage(data, "ig_scraper"),
    },
    {
      label: "Social Media Reports",
      value: getFeatureUsage(data, "social_media_report"),
    },
    {
      label: "Reputation Strategy",
      value: getFeatureUsage(data, "reputation_strategy"),
    },
  ]

  return (
    <Container maxW="full">
      <Heading size="sm" py={4}>
        Payments
      </Heading>

      <Box layerStyle="dashboardCard" p={{ base: 5, md: 6 }}>
        <Flex
          direction={{ base: "column", lg: "row" }}
          justifyContent="space-between"
          gap={6}
        >
          <Box>
            <Flex alignItems="center" gap={3} wrap="wrap">
              <Text fontWeight="black" fontSize={{ base: "xl", md: "2xl" }}>
                {getBillingPlanLabel(data)}
              </Text>
              {data?.subscription_status ? (
                <Badge
                  rounded="full"
                  colorPalette={
                    subscriptionToneMap[data.subscription_status] ?? "green"
                  }
                  px={3}
                  py={1}
                >
                  {subscriptionLabelMap[data.subscription_status] ??
                    data.subscription_status}
                </Badge>
              ) : null}
            </Flex>
            <Text mt={3} color="ui.secondaryText">
              {periodPresentation.label}:{" "}
              <Text as="span" fontWeight="bold" color="inherit">
                {periodPresentation.value}
              </Text>
            </Text>
            {periodPresentation.helper ? (
              <Text mt={3} color="ui.secondaryText">
                {periodPresentation.helper}
              </Text>
            ) : null}
            {data?.pending_ambassador_activation ? (
              <Text mt={3} color="ui.secondaryText">
                Ambassador access is scheduled to activate at the end of the
                current billing period.
              </Text>
            ) : null}
            {data?.access_revoked_reason ? (
              <Text mt={3} color="ui.dangerText">
                Access revoked reason: {data.access_revoked_reason}
              </Text>
            ) : null}
          </Box>

          <Flex
            alignItems={{ base: "stretch", lg: "flex-start" }}
            justifyContent="flex-end"
            gap={3}
            flexDirection={{ base: "column", sm: "row" }}
          >
            {showCheckoutCta ? (
              <Button
                layerStyle="brandGradientButton"
                loading={checkoutMutation.isPending}
                onClick={() => checkoutMutation.mutate()}
              >
                {checkoutLabel}
              </Button>
            ) : null}
            {!isManagedAccess &&
            data?.billing_eligible &&
            data?.subscription_status &&
            !["canceled", "incomplete_expired"].includes(
              data.subscription_status,
            ) ? (
              <Button
                variant="outline"
                loading={portalMutation.isPending}
                onClick={() => portalMutation.mutate()}
              >
                {portalLabel}
              </Button>
            ) : null}
          </Flex>
        </Flex>

        <Grid
          mt={6}
          templateColumns={{ base: "1fr", md: "repeat(3, minmax(0, 1fr))" }}
          gap={4}
        >
          {featureCards.map((item) => (
            <Box
              key={item.label}
              rounded="2xl"
              borderWidth="1px"
              borderColor="ui.border"
              bg="ui.surfaceSoft"
              px={4}
              py={4}
            >
              <Text color="ui.secondaryText" fontSize="sm" fontWeight="bold">
                {item.label}
              </Text>
              <Text mt={3} fontSize="2xl" fontWeight="black">
                {renderFeatureUsageValue(item.value)}
              </Text>
            </Box>
          ))}
        </Grid>

        {isLoading ? (
          <Text mt={4} color="ui.secondaryText">
            Loading billing details...
          </Text>
        ) : null}

        {data?.notices?.length ? (
          <Box mt={6}>
            <Text fontWeight="black" mb={3}>
              Billing notices
            </Text>
            <Grid gap={3}>
              {data.notices.map((notice) => (
                <Box
                  key={notice.id}
                  rounded="xl"
                  borderWidth="1px"
                  borderColor="ui.border"
                  bg="ui.surfaceSoft"
                  px={4}
                  py={4}
                >
                  <Flex align="center" justify="space-between" gap={3}>
                    <Text fontWeight="bold">{notice.title}</Text>
                    <Badge colorPalette={noticeToneMap[notice.notice_type]}>
                      {notice.status}
                    </Badge>
                  </Flex>
                  <Text mt={2} color="ui.secondaryText" fontSize="sm">
                    {notice.message}
                  </Text>
                </Box>
              ))}
            </Grid>
          </Box>
        ) : null}
      </Box>
    </Container>
  )
}

export default Payments
