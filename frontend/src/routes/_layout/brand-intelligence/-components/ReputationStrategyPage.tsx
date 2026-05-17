import {
  Badge,
  Box,
  Flex,
  Heading,
  SimpleGrid,
  Skeleton,
  Text,
} from "@chakra-ui/react"
import { lazy, Suspense, useEffect, useState } from "react"
import { Trans, useTranslation } from "react-i18next"
import { FiTarget, FiUserCheck } from "react-icons/fi"
import { ImBlocked } from "react-icons/im"

import StrategyOptionCard from "@/components/BrandIntelligence/StrategyOptionCard"
import DashboardTopbar from "@/components/Dashboard/DashboardTopbar"

type StrategyType =
  | "reputation-campaign-strategy"
  | "reputation-creator-strategy"

const loadCampaignStrategyTab = () => import("./CampaignStrategyTab")
const loadCreatorStrategyTab = () => import("./CreatorStrategyTab")

const CampaignStrategyTab = lazy(loadCampaignStrategyTab)
const CreatorStrategyTab = lazy(loadCreatorStrategyTab)

const StrategyTabFallback = () => (
  <Box
    display="grid"
    gridTemplateColumns={{ base: "1fr", xl: "minmax(0, 1.65fr) 360px" }}
    gap={6}
  >
    <Flex direction="column" gap={6} minW={0}>
      <Box
        rounded="30px"
        borderWidth="1px"
        borderColor="ui.border"
        bg="ui.panel"
        boxShadow="ui.panel"
        px={{ base: 5, md: 6 }}
        py={{ base: 5, md: 6 }}
      >
        <Skeleton h="4" w="24" rounded="full" />
        <Skeleton mt={4} h="8" w="56" rounded="xl" />
        <Skeleton mt={3} h="4" rounded="full" />
        <Skeleton mt={6} h="14" rounded="2xl" />
        <Skeleton mt={4} h="14" rounded="2xl" />
        <Skeleton mt={4} h="14" rounded="2xl" />
      </Box>
      <Skeleton h="320px" rounded="3xl" />
      <Skeleton h="280px" rounded="3xl" />
    </Flex>

    <Flex direction="column" gap={6}>
      <Skeleton h="260px" rounded="3xl" />
      <Skeleton h="220px" rounded="3xl" />
    </Flex>
  </Box>
)

export function ReputationStrategyPage() {
  const { t } = useTranslation("brandIntelligence")
  const [selectedStrategy, setSelectedStrategy] = useState<StrategyType>(
    "reputation-campaign-strategy",
  )
  const [mountedStrategies, setMountedStrategies] = useState<
    Record<StrategyType, boolean>
  >({
    "reputation-campaign-strategy": true,
    "reputation-creator-strategy": false,
  })

  useEffect(() => {
    void loadCampaignStrategyTab()
  }, [])

  const handleSelectStrategy = (strategy: StrategyType) => {
    setSelectedStrategy(strategy)
    setMountedStrategies((current) =>
      current[strategy] ? current : { ...current, [strategy]: true },
    )
  }

  const isCampaignSelected = selectedStrategy === "reputation-campaign-strategy"
  const isCreatorSelected = selectedStrategy === "reputation-creator-strategy"

  return (
    <Box minH="100vh" bg="ui.page">
      <DashboardTopbar />

      <Box px={{ base: 4, md: 7, lg: 10 }} py={{ base: 7, lg: 9 }}>
        <Flex
          mb={{ base: 7, lg: 8 }}
          alignItems={{ base: "flex-start", lg: "flex-start" }}
          justifyContent="space-between"
          gap={{ base: 4, lg: 6 }}
          direction={{ base: "column", lg: "row" }}
        >
          <Box flex="1" minW={0}>
            <Text textStyle="eyebrow">{t("page.eyebrow")}</Text>
            <Heading
              mt={3}
              textStyle="pageTitle"
              fontSize={{ base: "3xl", lg: "4xl" }}
              fontWeight="black"
              lineHeight="1.05"
              maxW="18ch"
            >
              {t("page.title")}
            </Heading>
            <Text
              mt={3}
              color="ui.secondaryText"
              fontSize={{ base: "md", lg: "lg" }}
              maxW="70ch"
            >
              {t("page.description")}
            </Text>
          </Box>

          <Flex
            gap={2}
            wrap="wrap"
            alignSelf={{ base: "stretch", lg: "flex-start" }}
          >
            <Badge
              rounded="full"
              bg="ui.brandSoft"
              color="ui.brandText"
              px={3}
              py={1.5}
            >
              {t("page.badges.validationFirst")}
            </Badge>
            <Badge
              rounded="full"
              bg="ui.surfaceSoft"
              color="ui.secondaryText"
              px={3}
              py={1.5}
            >
              {t("page.badges.pdfOnly")}
            </Badge>
            <Badge
              rounded="full"
              bg="ui.surfaceSoft"
              color="ui.secondaryText"
              px={3}
              py={1.5}
            >
              {t("page.badges.localReportsSynced")}
            </Badge>
          </Flex>
        </Flex>

        <SimpleGrid
          columns={{ base: 1, xl: 2 }}
          gap={5}
          mb={{ base: 7, lg: 8 }}
        >
          <StrategyOptionCard
            description={t("page.strategyOptions.campaign.description")}
            icon={FiTarget}
            isActive={isCampaignSelected}
            onMouseEnter={() => void loadCampaignStrategyTab()}
            onFocus={() => void loadCampaignStrategyTab()}
            onClick={() => handleSelectStrategy("reputation-campaign-strategy")}
            title={t("page.strategyOptions.campaign.title")}
          />
          <StrategyOptionCard
            description={t("page.strategyOptions.creator.description")}
            icon={FiUserCheck}
            isActive={isCreatorSelected}
            onMouseEnter={() => void loadCreatorStrategyTab()}
            onFocus={() => void loadCreatorStrategyTab()}
            onClick={() => handleSelectStrategy("reputation-creator-strategy")}
            title={t("page.strategyOptions.creator.title")}
          />
        </SimpleGrid>

        <Box
          mb={{ base: 6, lg: 7 }}
          rounded="3xl"
          borderWidth="1px"
          borderColor="ui.border"
          bg="ui.panel"
          px={{ base: 5, md: 6 }}
          py={{ base: 5, md: 6 }}
        >
          <Flex alignItems="flex-start" gap={3}>
            <Flex
              boxSize="10"
              flexShrink={0}
              alignItems="center"
              justifyContent="center"
              rounded="2xl"
              bg="ui.brandSoft"
              color="ui.brandText"
            >
              <ImBlocked />
            </Flex>
            <Box>
              <Text fontWeight="black">{t("page.mandatoryGate.title")}</Text>
              <Text mt={1} color="ui.secondaryText">
                <Trans
                  i18nKey="page.mandatoryGate.description"
                  ns="brandIntelligence"
                  components={{
                    strong: (
                      <Text as="span" fontWeight="bold" color="inherit" />
                    ),
                  }}
                />
              </Text>
            </Box>
          </Flex>
        </Box>

        {mountedStrategies["reputation-campaign-strategy"] ? (
          <Box display={isCampaignSelected ? "block" : "none"}>
            <Suspense fallback={<StrategyTabFallback />}>
              <CampaignStrategyTab />
            </Suspense>
          </Box>
        ) : null}
        {mountedStrategies["reputation-creator-strategy"] ? (
          <Box display={isCreatorSelected ? "block" : "none"}>
            <Suspense fallback={<StrategyTabFallback />}>
              <CreatorStrategyTab />
            </Suspense>
          </Box>
        ) : null}
      </Box>
    </Box>
  )
}
