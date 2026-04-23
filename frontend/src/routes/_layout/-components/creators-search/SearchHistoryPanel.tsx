import { Box, Flex, Heading, Text } from "@chakra-ui/react"

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
}) => (
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
          SEARCH HISTORY
        </Text>
        <Heading mt={2} size="md">
          Search history
        </Heading>
        <Text mt={2} color="ui.secondaryText">
          Keep the last ready username lists one click away.
        </Text>
      </Box>

      {items.length ? (
        <Button
          variant="outline"
          alignSelf={{ base: "stretch", md: "flex-start" }}
          onClick={onViewAll}
        >
          View all
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
          Search history is temporarily unavailable.
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
          No search history available yet.
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
