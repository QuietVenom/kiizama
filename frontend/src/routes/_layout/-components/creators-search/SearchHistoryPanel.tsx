import { Badge, Box, Flex, Icon, Text } from "@chakra-ui/react"
import { useTranslation } from "react-i18next"
import { FiChevronDown, FiChevronRight } from "react-icons/fi"

import type { CreatorsSearchHistoryItem } from "@/client"

import { ResultSkeletonCard } from "./ResultSkeletonCard"
import { SearchHistoryCard } from "./SearchHistoryCard"

export const SearchHistoryPanel = ({
  collapsed = false,
  isError,
  isLoading,
  items,
  onReuseReadyUsernames,
  onToggleCollapsed,
}: {
  collapsed?: boolean
  isError: boolean
  isLoading: boolean
  items: CreatorsSearchHistoryItem[]
  onReuseReadyUsernames: (usernames: string[]) => void
  onToggleCollapsed?: () => void
}) => {
  const { t } = useTranslation("creatorsSearch")

  return (
    <Box
      layerStyle="dashboardCard"
      p={{ base: 5, md: 6 }}
      mb={{ base: 6, lg: 7 }}
    >
      <Flex
        as={onToggleCollapsed ? "button" : "div"}
        w="full"
        alignItems="center"
        justifyContent="space-between"
        gap={3}
        textAlign="left"
        onClick={onToggleCollapsed}
      >
        <Flex alignItems="center" gap={2.5}>
          <Icon
            as={collapsed ? FiChevronRight : FiChevronDown}
            boxSize={4}
            color="ui.mutedText"
          />
          <Text textStyle="eyebrow">{t("history.title")}</Text>
        </Flex>
        <Badge
          rounded="full"
          borderWidth="1px"
          borderColor="ui.borderSoft"
          bg="ui.surfaceSoft"
          color="ui.secondaryText"
          px={3}
          py={1.5}
        >
          {t("history.count", { count: items.length, max: 20 })}
        </Badge>
      </Flex>

      {collapsed ? null : isLoading ? (
        <Flex
          mt={4}
          direction="row"
          gap={3}
          overflowX="auto"
          overflowY="hidden"
          pb={1}
        >
          <ResultSkeletonCard />
        </Flex>
      ) : isError ? (
        <Box
          mt={4}
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
          mt={4}
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
        <Box mt={4} overflowX="auto" overflowY="hidden" pb={1}>
          <Box
            display="grid"
            gridAutoFlow="column"
            gridAutoColumns={{
              base: "210px",
              md: "220px",
            }}
            gap={3}
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
