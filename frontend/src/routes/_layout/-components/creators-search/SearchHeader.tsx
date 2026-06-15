import { Box, Flex, Text } from "@chakra-ui/react"
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
        <Text
          color="ui.text"
          fontSize={{ base: "2xl", md: "3xl", lg: "4xl" }}
          fontWeight="black"
          letterSpacing="-0.03em"
          lineHeight="1.05"
          maxW="20ch"
        >
          {t("header.eyebrow")}
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
