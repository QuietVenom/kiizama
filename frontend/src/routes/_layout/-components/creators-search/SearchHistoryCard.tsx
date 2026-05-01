import { Badge, Box, Flex, Text } from "@chakra-ui/react"

import type { CreatorsSearchHistoryItem } from "@/client"

import { formatJobTimestamp } from "./creators-search.logic"

export const SearchHistoryCard = ({
  compact = false,
  item,
  onClick,
}: {
  compact?: boolean
  item: CreatorsSearchHistoryItem
  onClick: (usernames: string[]) => void
}) => {
  const readyUsernames = item.ready_usernames ?? []
  const visibleUsernames = readyUsernames.slice(0, 5)
  const hiddenUsernamesCount = Math.max(
    readyUsernames.length - visibleUsernames.length,
    0,
  )

  if (compact) {
    return (
      <Box
        as="button"
        rounded="2xl"
        borderWidth="1px"
        borderColor="ui.border"
        bg="ui.surfaceSoft"
        p={4}
        minH="0"
        aspectRatio={1}
        display="flex"
        flexDirection="column"
        textAlign="left"
        transition="transform 180ms ease, box-shadow 180ms ease, border-color 180ms ease"
        cursor="pointer"
        _hover={{
          boxShadow: "md",
          borderColor: "ui.brandText",
        }}
        onClick={() => onClick(readyUsernames)}
      >
        <Flex alignItems="flex-start" justifyContent="space-between" gap={3}>
          <Text color="ui.text" fontWeight="black" lineClamp={2} minW={0}>
            {item.source === "ig-scrape-job" && item.job_id
              ? item.job_id
              : "Direct search"}
          </Text>
          <Badge
            rounded="full"
            borderWidth="1px"
            borderColor="ui.borderSoft"
            bg="ui.panel"
            color="ui.brandText"
            px={3}
            py={1.5}
            flexShrink={0}
          >
            {readyUsernames.length}
          </Badge>
        </Flex>

        <Text mt={3} color="ui.secondaryText" fontSize="sm">
          {formatJobTimestamp(item.created_at)}
        </Text>

        <Flex mt={4} gap={2} wrap="wrap" alignContent="flex-start">
          {visibleUsernames.map((username) => (
            <Badge
              key={`${item.id}-${username}`}
              rounded="full"
              borderWidth="1px"
              borderColor="ui.borderSoft"
              bg="ui.panel"
              color="ui.text"
              px={3}
              py={1.5}
            >
              @{username}
            </Badge>
          ))}
          {hiddenUsernamesCount > 0 ? (
            <Badge
              rounded="full"
              borderWidth="1px"
              borderColor="ui.borderSoft"
              bg="ui.panel"
              color="ui.secondaryText"
              px={3}
              py={1.5}
            >
              +{hiddenUsernamesCount}
            </Badge>
          ) : null}
        </Flex>
      </Box>
    )
  }

  return (
    <Box
      as="button"
      rounded="2xl"
      borderWidth="1px"
      borderColor="ui.border"
      bg="ui.surfaceSoft"
      px={4}
      py={4}
      textAlign="left"
      transition="transform 180ms ease, box-shadow 180ms ease, border-color 180ms ease"
      cursor="pointer"
      _hover={{
        transform: "translateY(-1px)",
        boxShadow: "md",
        borderColor: "ui.brandText",
      }}
      onClick={() => onClick(readyUsernames)}
    >
      <Flex alignItems="flex-start" justifyContent="space-between" gap={3}>
        <Box minW={0}>
          <Text color="ui.text" fontWeight="black">
            {item.source === "ig-scrape-job" && item.job_id
              ? item.job_id
              : "Direct search"}
          </Text>
          <Text mt={1} color="ui.secondaryText" fontSize="sm">
            {item.source === "ig-scrape-job"
              ? "Ready usernames from scrape job"
              : "Ready usernames from direct search"}
          </Text>
        </Box>
        <Badge
          rounded="full"
          borderWidth="1px"
          borderColor="ui.borderSoft"
          bg="ui.panel"
          color="ui.brandText"
          px={3}
          py={1.5}
        >
          {readyUsernames.length}
        </Badge>
      </Flex>

      <Text mt={3} color="ui.secondaryText" fontSize="sm">
        {formatJobTimestamp(item.created_at)}
      </Text>

      <Flex mt={3} gap={2} wrap="wrap">
        {readyUsernames.map((username) => (
          <Badge
            key={`${item.id}-${username}`}
            rounded="full"
            borderWidth="1px"
            borderColor="ui.borderSoft"
            bg="ui.panel"
            color="ui.text"
            px={3}
            py={1.5}
          >
            @{username}
          </Badge>
        ))}
      </Flex>
    </Box>
  )
}
