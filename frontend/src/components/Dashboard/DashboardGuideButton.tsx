import {
  Box,
  Button,
  Flex,
  Heading,
  IconButton,
  Image,
  Text,
} from "@chakra-ui/react"
import { useState } from "react"
import { useTranslation } from "react-i18next"
import { FiBookOpen } from "react-icons/fi"

import {
  DialogBody,
  DialogCloseTrigger,
  DialogContent,
  DialogHeader,
  DialogRoot,
  DialogTitle,
} from "@/components/ui/dialog"

const GUIDE_ITEMS = [
  {
    key: "dashboard",
    src: "/assets/kiizama-guide/01-dashboard-guide.webp",
  },
  {
    key: "directSearch",
    src: "/assets/kiizama-guide/02-creator-search-direct-guide.webp",
  },
  {
    key: "explore",
    src: "/assets/kiizama-guide/03-creator-search-explore-guide.webp",
  },
] as const

export const DashboardGuideButton = () => {
  const { t } = useTranslation("common")
  const [isOpen, setIsOpen] = useState(false)
  const [activeKey, setActiveKey] =
    useState<(typeof GUIDE_ITEMS)[number]["key"]>("dashboard")
  const activeItem =
    GUIDE_ITEMS.find((item) => item.key === activeKey) ?? GUIDE_ITEMS[0]

  return (
    <>
      <IconButton
        aria-label={t("guide.trigger")}
        variant="outline"
        rounded="2xl"
        onClick={() => setIsOpen(true)}
      >
        <FiBookOpen />
      </IconButton>

      <DialogRoot
        open={isOpen}
        placement="center"
        onOpenChange={({ open }) => setIsOpen(open)}
      >
        <DialogContent
          display="flex"
          flexDirection="column"
          w={{ base: "calc(100vw - 1rem)", lg: "86vw" }}
          maxW={{ base: "calc(100vw - 1rem)", lg: "86vw" }}
          h={{ base: "calc(100vh - 1rem)", lg: "86vh" }}
          maxH={{ base: "calc(100vh - 1rem)", lg: "86vh" }}
          overflow="hidden"
          rounded="4xl"
          borderWidth="1px"
          borderColor="ui.border"
          bg="ui.page"
        >
          <DialogCloseTrigger />
          <DialogHeader
            borderBottomWidth="1px"
            borderBottomColor="ui.border"
            bg="ui.panel"
            px={{ base: 5, md: 6 }}
            py={{ base: 4, md: 5 }}
          >
            <DialogTitle
              display="inline-flex"
              alignItems="center"
              gap={2.5}
              fontSize={{ base: "lg", md: "xl" }}
              fontWeight="black"
            >
              <FiBookOpen />
              {t("guide.title")}
            </DialogTitle>
          </DialogHeader>

          <DialogBody p={0} flex="1" overflow="hidden">
            <Flex h="full" direction={{ base: "column", lg: "row" }}>
              <Box
                w={{ base: "full", lg: "300px" }}
                flexShrink={0}
                borderRightWidth={{ base: 0, lg: "1px" }}
                borderBottomWidth={{ base: "1px", lg: 0 }}
                borderColor="ui.border"
                bg="ui.panel"
                p={{ base: 4, lg: 5 }}
              >
                <Text
                  color="ui.mutedText"
                  fontSize="xs"
                  fontWeight="bold"
                  textTransform="uppercase"
                >
                  {t("guide.sectionsLabel")}
                </Text>
                <Flex
                  mt={3}
                  direction={{ base: "row", lg: "column" }}
                  gap={2}
                  overflowX={{ base: "auto", lg: "visible" }}
                  pb={{ base: 1, lg: 0 }}
                >
                  {GUIDE_ITEMS.map((item, index) => {
                    const isActive = item.key === activeItem.key
                    return (
                      <Button
                        key={item.key}
                        justifyContent="flex-start"
                        minW={{ base: "max-content", lg: "auto" }}
                        variant={isActive ? "solid" : "ghost"}
                        bg={isActive ? "ui.activeSoft" : undefined}
                        color={isActive ? "ui.text" : "ui.secondaryText"}
                        borderWidth={isActive ? "1px" : 0}
                        borderColor="ui.border"
                        rounded="2xl"
                        onClick={() => setActiveKey(item.key)}
                      >
                        {index + 1}. {t(`guide.items.${item.key}.title`)}
                      </Button>
                    )
                  })}
                </Flex>
              </Box>

              <Box flex="1" minW={0} overflow="auto" p={{ base: 4, lg: 6 }}>
                <Box maxW="1280px" mx="auto">
                  <Heading fontSize={{ base: "xl", md: "2xl" }}>
                    {t(`guide.items.${activeItem.key}.title`)}
                  </Heading>
                  <Text mt={2} color="ui.secondaryText">
                    {t(`guide.items.${activeItem.key}.description`)}
                  </Text>
                  <Box
                    mt={5}
                    rounded="3xl"
                    borderWidth="1px"
                    borderColor="ui.border"
                    bg="ui.panel"
                    overflow="hidden"
                    boxShadow="ui.card"
                  >
                    <Image
                      src={activeItem.src}
                      alt={t(`guide.items.${activeItem.key}.imageAlt`)}
                      display="block"
                      w="full"
                      h="auto"
                    />
                  </Box>
                </Box>
              </Box>
            </Flex>
          </DialogBody>
        </DialogContent>
      </DialogRoot>
    </>
  )
}
