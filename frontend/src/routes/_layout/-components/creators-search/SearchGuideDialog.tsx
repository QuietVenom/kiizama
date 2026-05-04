import { Box, Flex, Icon, Text } from "@chakra-ui/react"
import { useTranslation } from "react-i18next"
import { FiClock, FiSearch, FiShield } from "react-icons/fi"

import { Button } from "@/components/ui/button"
import {
  DialogBody,
  DialogContent,
  DialogFooter,
  DialogHeader,
  DialogRoot,
  DialogTitle,
} from "@/components/ui/dialog"

const GuideItem = ({
  description,
  icon,
  title,
}: {
  description: string
  icon: typeof FiSearch
  title: string
}) => (
  <Flex
    alignItems="flex-start"
    gap={3}
    rounded="2xl"
    borderWidth="1px"
    borderColor="ui.border"
    bg="ui.surfaceSoft"
    px={4}
    py={4}
  >
    <Flex
      boxSize="10"
      flexShrink={0}
      alignItems="center"
      justifyContent="center"
      rounded="2xl"
      bg="ui.brandSoft"
      color="ui.brandText"
    >
      <Icon as={icon} boxSize={5} />
    </Flex>
    <Box>
      <Text fontWeight="bold">{title}</Text>
      <Text mt={1} color="ui.secondaryText" fontSize="sm">
        {description}
      </Text>
    </Box>
  </Flex>
)

export const SearchGuideDialog = ({
  onOpenChange,
  open,
}: {
  onOpenChange: (open: boolean) => void
  open: boolean
}) => {
  const { t } = useTranslation(["creatorsSearch", "common"])

  return (
    <DialogRoot
      open={open}
      placement="center"
      onOpenChange={({ open }) => onOpenChange(open)}
    >
      <DialogContent
        maxW={{ base: "calc(100vw - 1rem)", md: "680px" }}
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
            {t("creatorsSearch:guide.title")}
          </DialogTitle>
          <Text mt={2} color="ui.secondaryText">
            {t("creatorsSearch:guide.description")}
          </Text>
        </DialogHeader>

        <DialogBody px={{ base: 5, md: 6 }} py={{ base: 5, md: 6 }}>
          <Flex direction="column" gap={3}>
            <GuideItem
              icon={FiSearch}
              title={t("creatorsSearch:guide.items.multiCreator.title")}
              description={t(
                "creatorsSearch:guide.items.multiCreator.description",
              )}
            />
            <GuideItem
              icon={FiClock}
              title={t("creatorsSearch:guide.items.savedDetails.title")}
              description={t(
                "creatorsSearch:guide.items.savedDetails.description",
              )}
            />
            <GuideItem
              icon={FiShield}
              title={t("creatorsSearch:guide.items.issueHighlighting.title")}
              description={t(
                "creatorsSearch:guide.items.issueHighlighting.description",
              )}
            />
          </Flex>
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
