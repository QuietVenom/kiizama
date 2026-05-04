import { Box, Flex, Heading, Text } from "@chakra-ui/react"
import { useTranslation } from "react-i18next"
import { FiInfo } from "react-icons/fi"

import { Button } from "@/components/ui/button"

export const SearchHeader = ({ onOpenGuide }: { onOpenGuide: () => void }) => {
  const { t } = useTranslation("creatorsSearch")

  return (
    <Flex
      mb={{ base: 7, lg: 8 }}
      alignItems={{ base: "flex-start", lg: "flex-start" }}
      justifyContent="space-between"
      gap={{ base: 4, lg: 6 }}
      direction={{ base: "column", lg: "row" }}
    >
      <Box flex="1" minW={0}>
        <Text textStyle="eyebrow">{t("header.eyebrow")}</Text>
        <Heading
          mt={3}
          textStyle="pageTitle"
          fontSize={{ base: "3xl", lg: "4xl" }}
          fontWeight="black"
          lineHeight="1.05"
          maxW="24ch"
        >
          {t("header.title")}
        </Heading>
        <Text
          mt={3}
          color="ui.secondaryText"
          fontSize={{ base: "md", lg: "lg" }}
          maxW="68ch"
        >
          {t("header.description")}
        </Text>
      </Box>

      <Button
        variant="outline"
        alignSelf={{ base: "stretch", lg: "flex-start" }}
        onClick={onOpenGuide}
      >
        <FiInfo />
        {t("header.guideButton")}
      </Button>
    </Flex>
  )
}
