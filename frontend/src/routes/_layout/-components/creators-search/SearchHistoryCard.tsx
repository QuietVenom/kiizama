import { Badge, Box, Flex, Text } from "@chakra-ui/react"
import { useTranslation } from "react-i18next"

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
  const { i18n, t } = useTranslation("creatorsSearch")
  const readyUsernames = item.ready_usernames ?? []
  const previewUsernames = readyUsernames.slice(0, 5)
  const compactPreviewText =
    readyUsernames.length > 5
      ? `${previewUsernames.map((username) => `@${username}`).join(", ")}...`
      : previewUsernames.map((username) => `@${username}`).join(", ")

  if (compact) {
    return (
      <Box
        as="button"
        rounded="2xl"
        borderWidth="1px"
        borderColor="ui.border"
        bg="ui.surfaceSoft"
        px={3.5}
        py={3.5}
        minW={{ base: "210px", md: "220px" }}
        maxW={{ base: "240px", md: "240px" }}
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
          <Text
            color="ui.text"
            fontSize="2xs"
            fontWeight="black"
            lineClamp={2}
            minW={0}
          >
            {item.source === "ig-scrape-job" && item.job_id
              ? item.job_id
              : t("history.card.directSearch")}
          </Text>
          <Badge
            rounded="full"
            borderWidth="1px"
            borderColor="ui.borderSoft"
            bg="ui.panel"
            color="ui.brandText"
            px={2.5}
            py={1}
            fontSize="2xs"
            flexShrink={0}
          >
            {readyUsernames.length}
          </Badge>
        </Flex>

        <Text
          mt={2.5}
          color="ui.secondaryText"
          fontSize="xs"
          lineHeight="1.45"
          lineClamp={3}
        >
          {compactPreviewText}
        </Text>
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
              : t("history.card.directSearch")}
          </Text>
          <Text mt={1} color="ui.secondaryText" fontSize="sm">
            {item.source === "ig-scrape-job"
              ? t("history.card.fromJob")
              : t("history.card.fromDirect")}
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
        {formatJobTimestamp(
          item.created_at,
          i18n.resolvedLanguage ?? i18n.language,
        )}
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
