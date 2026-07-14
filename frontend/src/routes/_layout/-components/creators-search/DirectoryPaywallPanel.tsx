import { Box, Flex, Heading, Text } from "@chakra-ui/react"
import { useNavigate } from "@tanstack/react-router"
import { useTranslation } from "react-i18next"
import { FiLock } from "react-icons/fi"

import { Button } from "@/components/ui/button"

export function DirectoryPaywallPanel({
  trialEligible,
}: {
  trialEligible: boolean
}) {
  const { t } = useTranslation("creatorsSearch")
  const navigate = useNavigate()

  return (
    <Box
      rounded="28px"
      borderWidth="1px"
      borderColor="ui.border"
      bg="ui.panel"
      boxShadow="ui.card"
      px={{ base: 5, md: 8 }}
      py={{ base: 10, md: 14 }}
      textAlign="center"
      data-testid="directory-paywall-panel"
    >
      <Flex
        boxSize="12"
        mx="auto"
        rounded="full"
        align="center"
        justify="center"
        bg="ui.warningSoft"
        color="ui.warningText"
      >
        <FiLock size={20} />
      </Flex>

      <Text mt={5} color="ui.mutedText" fontSize="xs" fontWeight="bold">
        {t("directoryPaywall.eyebrow")}
      </Text>
      <Heading mt={2} fontSize={{ base: "xl", md: "2xl" }}>
        {t("directoryPaywall.title")}
      </Heading>
      <Text mt={3} mx="auto" maxW="52ch" color="ui.secondaryText">
        {t("directoryPaywall.description")}
      </Text>

      <Button
        mt={6}
        layerStyle="brandGradientButton"
        onClick={() =>
          navigate({
            to: "/settings",
            search: { tab: "payments" },
          })
        }
      >
        {trialEligible
          ? t("directoryPaywall.ctaTrial")
          : t("directoryPaywall.ctaSubscribe")}
      </Button>
    </Box>
  )
}

export default DirectoryPaywallPanel
