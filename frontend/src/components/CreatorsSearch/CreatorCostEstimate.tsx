import { Box, Flex, Text } from "@chakra-ui/react"
import { useQuery } from "@tanstack/react-query"
import { useTranslation } from "react-i18next"

import { BrandIntelligenceService, type CostTierCatalogItem } from "@/client"
import { formatNumber } from "@/i18n"

export const resolveCreatorCostTier = (
  followerCount: number | null | undefined,
  tiers: CostTierCatalogItem[],
) =>
  typeof followerCount === "number"
    ? tiers.find(
        (tier) =>
          !tier.is_manual &&
          (tier.min_followers == null || followerCount >= tier.min_followers) &&
          (tier.max_followers == null || followerCount <= tier.max_followers),
      )
    : undefined

export function CreatorCostEstimate({
  followerCount,
}: {
  followerCount: number | null | undefined
}) {
  const { i18n, t } = useTranslation("creatorsSearch")
  const { data: tiers, isError } = useQuery({
    queryKey: ["creator-cost-tiers"],
    queryFn: () => BrandIntelligenceService.readCostTiers(),
    staleTime: 60 * 60 * 1000,
    enabled: typeof followerCount === "number" && followerCount >= 1_000,
  })
  const tier = resolveCreatorCostTier(followerCount, tiers ?? [])
  const language = i18n.resolvedLanguage ?? i18n.language
  const prices = tier
    ? [
        {
          label: t("costEstimate.low"),
          amount: tier.min_mxn,
          description: t("costEstimate.lowDescription"),
        },
        {
          label: t("costEstimate.average"),
          amount: tier.average_mxn,
          description: t("costEstimate.averageDescription"),
        },
        {
          label: t("costEstimate.high"),
          amount: tier.max_mxn,
          description: t(
            tier.key === "mega"
              ? "costEstimate.highDescriptionMega"
              : "costEstimate.highDescription",
          ),
        },
      ]
    : []

  return (
    <Box
      as="section"
      aria-label={t("costEstimate.title")}
      mt={5}
      rounded="3xl"
      borderWidth="1px"
      borderColor="ui.border"
      bg="ui.panel"
      p={{ base: 4, md: 5 }}
    >
      <Flex align="flex-start" justify="space-between" gap={3} wrap="wrap">
        <Box>
          <Text as="h3" color="ui.text" fontSize="md" fontWeight="black">
            {t("costEstimate.title")}
          </Text>
          <Text mt={1} color="ui.secondaryText" fontSize="sm">
            {t("costEstimate.deliverable")}
          </Text>
        </Box>
        {tier ? (
          <Text
            rounded="full"
            borderWidth="1px"
            borderColor="ui.borderSoft"
            bg="ui.brandSoft"
            color="ui.brandText"
            px={3}
            py={1}
            fontSize="xs"
            fontWeight="bold"
          >
            {tier.label}
          </Text>
        ) : null}
      </Flex>
      {tier ? (
        <>
          <Box
            mt={4}
            display="grid"
            gridTemplateColumns={{
              base: "1fr",
              sm: "repeat(3, minmax(0, 1fr))",
            }}
            gap={2}
          >
            {prices.map(({ label, amount, description }) => (
              <Box
                key={label}
                rounded="2xl"
                borderWidth="1px"
                borderColor="ui.borderSoft"
                bg="ui.surfaceSoft"
                px={3.5}
                py={3}
              >
                <Text color="ui.secondaryText" fontSize="xs" fontWeight="bold">
                  {label}
                </Text>
                <Text
                  mt={1}
                  color="ui.text"
                  fontSize={{ base: "lg", md: "xl" }}
                  fontWeight="black"
                  lineHeight="1.2"
                  overflowWrap="anywhere"
                >
                  {formatNumber(amount, language)}
                </Text>
                <Text color="ui.mutedText" fontSize="xs" fontWeight="semibold">
                  MXN
                </Text>
                <Text
                  mt={3}
                  pt={3}
                  borderTopWidth="1px"
                  borderColor="ui.borderSoft"
                  color="ui.secondaryText"
                  fontSize="xs"
                  lineHeight="1.5"
                >
                  {description}
                </Text>
              </Box>
            ))}
          </Box>
          <Text
            mt={4}
            color="ui.secondaryText"
            fontSize="xs"
            fontWeight="medium"
          >
            {t("costEstimate.disclaimer")}
          </Text>
        </>
      ) : (
        <Text mt={4} color="ui.secondaryText" fontSize="sm">
          {t(
            isError
              ? "costEstimate.error"
              : followerCount == null || followerCount < 1_000 || tiers
                ? "costEstimate.unavailable"
                : "costEstimate.loading",
          )}
        </Text>
      )}
    </Box>
  )
}
