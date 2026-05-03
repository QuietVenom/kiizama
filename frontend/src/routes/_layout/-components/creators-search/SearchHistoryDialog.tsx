import { Box, Flex, Text } from "@chakra-ui/react"
import { useTranslation } from "react-i18next"

import type { CreatorsSearchHistoryItem } from "@/client"
import { Button } from "@/components/ui/button"
import {
  DialogBody,
  DialogContent,
  DialogFooter,
  DialogHeader,
  DialogRoot,
  DialogTitle,
} from "@/components/ui/dialog"

import { ResultSkeletonCard } from "./ResultSkeletonCard"
import { SearchHistoryCard } from "./SearchHistoryCard"

export const SearchHistoryDialog = ({
  items,
  loading,
  onOpenChange,
  onReuseReadyUsernames,
  open,
}: {
  items: CreatorsSearchHistoryItem[]
  loading: boolean
  onOpenChange: (open: boolean) => void
  onReuseReadyUsernames: (usernames: string[]) => void
  open: boolean
}) => {
  const { t } = useTranslation(["creatorsSearch", "common"])

  return (
    <DialogRoot
      open={open}
      placement="center"
      onOpenChange={({ open: nextOpen }) => onOpenChange(nextOpen)}
    >
      <DialogContent
        maxW={{ base: "calc(100vw - 1rem)", md: "860px" }}
        maxH={{ base: "calc(100vh - 1rem)", md: "calc(100vh - 4rem)" }}
        overflow="hidden"
        rounded="4xl"
        borderWidth="1px"
        borderColor="ui.border"
        bg="ui.page"
      >
        <DialogHeader
          borderBottomWidth="1px"
          borderBottomColor="ui.border"
          bg="ui.panel"
          px={{ base: 6, md: 7 }}
          py={{ base: 6, md: 7 }}
        >
          <DialogTitle
            display="inline-flex"
            alignItems="center"
            minH="10"
            fontSize={{ base: "xl", md: "2xl" }}
            fontWeight="black"
            letterSpacing="-0.02em"
            lineHeight="1"
            whiteSpace="nowrap"
          >
            {t("creatorsSearch:history.dialog.title")}
          </DialogTitle>
          <Text mt={2} color="ui.secondaryText">
            {t("creatorsSearch:history.dialog.description")}
          </Text>
        </DialogHeader>

        <DialogBody
          px={{ base: 5, md: 6 }}
          py={{ base: 5, md: 6 }}
          overflowY="auto"
        >
          {loading ? (
            <Flex direction="column" gap={3}>
              <ResultSkeletonCard />
              <ResultSkeletonCard />
            </Flex>
          ) : items.length === 0 ? (
            <Box
              rounded="2xl"
              borderWidth="1px"
              borderColor="ui.border"
              bg="ui.surfaceSoft"
              px={4}
              py={4}
            >
              <Text color="ui.secondaryText" fontSize="sm" fontWeight="bold">
                {t("creatorsSearch:history.empty")}
              </Text>
            </Box>
          ) : (
            <Flex direction="column" gap={3}>
              {items.map((item) => (
                <SearchHistoryCard
                  key={item.id}
                  item={item}
                  onClick={(usernames) => onReuseReadyUsernames(usernames)}
                />
              ))}
            </Flex>
          )}
        </DialogBody>

        <DialogFooter
          borderTopWidth="1px"
          borderTopColor="ui.border"
          bg="ui.panel"
          px={{ base: 5, md: 6 }}
          py={4}
        >
          <Button variant="outline" onClick={() => onOpenChange(false)}>
            {t("common:actions.close")}
          </Button>
        </DialogFooter>
      </DialogContent>
    </DialogRoot>
  )
}
