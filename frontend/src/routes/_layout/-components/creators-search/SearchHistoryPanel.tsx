import { Box, Flex, Heading, Text } from "@chakra-ui/react"
import { useTranslation } from "react-i18next"

import type { CreatorsSearchHistoryItem } from "@/client"
import { Button } from "@/components/ui/button"

import { ResultSkeletonCard } from "./ResultSkeletonCard"
import { SearchHistoryCard } from "./SearchHistoryCard"

export const SearchHistoryPanel = ({
  isError,
  isLoading,
  items,
  onReuseReadyUsernames,
  onViewAll,
}: {
  isError: boolean
  isLoading: boolean
  items: CreatorsSearchHistoryItem[]
  onReuseReadyUsernames: (usernames: string[]) => void
  onViewAll: () => void
}) => {
  const { t } = useTranslation("creatorsSearch")

  return (
    <Box
      layerStyle="dashboardCard"
      p={{ base: 6, md: 8 }}
      mb={{ base: 7, lg: 8 }}
    >
      <Flex
        alignItems={{ base: "flex-start", md: "center" }}
        justifyContent="space-between"
        gap={4}
        direction={{ base: "column", md: "row" }}
      >
        <Box>
          <Text
            fontSize="sm"
            color="ui.mutedText"
            fontWeight="bold"
            letterSpacing="0.08em"
          >
            {t("history.eyebrow")}
          </Text>
          <Heading mt={2} size="md">
            {t("history.title")}
          </Heading>
          <Text mt={2} color="ui.secondaryText">
            {t("history.description")}
          </Text>
        </Box>

        {items.length ? (
          <Button
            variant="outline"
            alignSelf={{ base: "stretch", md: "flex-start" }}
            onClick={onViewAll}
          >
            {t("history.viewAll")}
          </Button>
        ) : null}
      </Flex>

      {isLoading ? (
        <Flex mt={5} direction="column" gap={3}>
          <ResultSkeletonCard />
        </Flex>
      ) : isError ? (
        <Box
          mt={5}
          rounded="2xl"
          borderWidth="1px"
          borderColor="ui.border"
          bg="ui.surfaceSoft"
          px={4}
          py={4}
        >
          <Text color="ui.secondaryText" fontSize="sm" fontWeight="bold">
            {t("history.unavailable")}
          </Text>
        </Box>
      ) : items.length === 0 ? (
        <Box
          mt={5}
          rounded="2xl"
          borderWidth="1px"
          borderColor="ui.border"
          bg="ui.surfaceSoft"
          px={4}
          py={4}
        >
          <Text color="ui.secondaryText" fontSize="sm" fontWeight="bold">
            {t("history.empty")}
          </Text>
        </Box>
      ) : (
        <Box mt={7} overflowX="auto" overflowY="hidden" pb={2}>
          <Box
            display="grid"
            gridAutoFlow="column"
            gridAutoColumns={{
              base: "minmax(220px, 85%)",
              md: "minmax(210px, calc((100% - 2rem) / 3))",
              lg: "minmax(200px, calc((100% - 3rem) / 4))",
              xl: "minmax(190px, calc((100% - 4rem) / 5))",
            }}
            gap={4}
            alignItems="stretch"
          >
            {items.map((item) => (
              <SearchHistoryCard
                key={item.id}
                compact
                item={item}
                onClick={onReuseReadyUsernames}
              />
            ))}
          </Box>
        </Box>
      )}
    </Box>
  )
}
