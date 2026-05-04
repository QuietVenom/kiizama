import { Badge, Box, Flex, HStack, Icon, Spinner, Text } from "@chakra-ui/react"
import { useTranslation } from "react-i18next"
import { FiAlertCircle, FiCheckCircle, FiClock } from "react-icons/fi"
import type { ProfileExistenceItem } from "@/client"

type ProfileValidationPanelProps = {
  error?: string | null
  isLoading?: boolean
  isStale?: boolean
  profiles: ProfileExistenceItem[]
  usernames: string[]
}

const countCardStyles = {
  base: {
    rounded: "2xl",
    borderWidth: "1px",
    px: 4,
    py: 4,
  },
  brand: {
    bg: "ui.brandSoft",
    borderColor: "ui.brandBorderSoft",
    color: "ui.brandText",
  },
  danger: {
    bg: "ui.dangerSoft",
    borderColor: "ui.danger",
    color: "ui.dangerText",
  },
  warning: {
    bg: "ui.warningSoft",
    borderColor: "ui.warning",
    color: "ui.warningText",
  },
} as const

const ProfileValidationPanel = ({
  error,
  isLoading,
  isStale,
  profiles,
  usernames,
}: ProfileValidationPanelProps) => {
  const { t } = useTranslation("brandIntelligence")
  const existingProfiles = profiles.filter(
    (profile) => profile.exists && !profile.expired,
  )
  const expiredProfiles = profiles.filter(
    (profile) => profile.exists && profile.expired,
  )
  const missingProfiles = profiles.filter((profile) => !profile.exists)

  if (usernames.length === 0) {
    return (
      <Box
        rounded="3xl"
        borderWidth="1px"
        borderColor="ui.border"
        bg="ui.panel"
        px={5}
        py={5}
      >
        <Text fontWeight="bold">{t("validationPanel.title")}</Text>
        <Text mt={2} color="ui.secondaryText">
          {t("validationPanel.initialDescription")}
        </Text>
      </Box>
    )
  }

  if (isLoading && profiles.length === 0) {
    return (
      <Box
        rounded="3xl"
        borderWidth="1px"
        borderColor="ui.brandBorderSoft"
        bg="ui.brandSoft"
        px={5}
        py={5}
      >
        <Flex alignItems="center" gap={3}>
          <Spinner size="sm" color="ui.brandText" />
          <Box>
            <Text color="ui.brandText" fontWeight="bold">
              {t("validationPanel.loadingTitle")}
            </Text>
            <Text mt={1} color="ui.secondaryText">
              {t("validationPanel.loadingDescription")}
            </Text>
          </Box>
        </Flex>
      </Box>
    )
  }

  if (error && profiles.length === 0) {
    return (
      <Box
        rounded="3xl"
        borderWidth="1px"
        borderColor="ui.danger"
        bg="ui.dangerSoft"
        px={5}
        py={5}
      >
        <Flex alignItems="flex-start" gap={3}>
          <Icon as={FiAlertCircle} boxSize={5} color="ui.dangerText" mt={0.5} />
          <Box>
            <Text color="ui.dangerText" fontWeight="bold">
              {t("validationPanel.errorTitle")}
            </Text>
            <Text mt={1} color="ui.secondaryText">
              {error}
            </Text>
          </Box>
        </Flex>
      </Box>
    )
  }

  if (isStale) {
    return (
      <Box
        rounded="3xl"
        borderWidth="1px"
        borderColor="ui.warning"
        bg="ui.warningSoft"
        px={5}
        py={5}
      >
        <Flex alignItems="flex-start" gap={3}>
          <Icon as={FiClock} boxSize={5} color="ui.warningText" mt={0.5} />
          <Box>
            <Text color="ui.warningText" fontWeight="bold">
              {t("validationPanel.staleTitle")}
            </Text>
            <Text mt={1} color="ui.secondaryText">
              {t("validationPanel.staleDescription")}
            </Text>
          </Box>
        </Flex>
      </Box>
    )
  }

  if (profiles.length === 0) {
    return (
      <Box
        rounded="3xl"
        borderWidth="1px"
        borderColor="ui.border"
        bg="ui.panel"
        px={5}
        py={5}
      >
        <Text fontWeight="bold">{t("validationPanel.title")}</Text>
        <Text mt={2} color="ui.secondaryText">
          {t("validationPanel.preValidationDescription")}
        </Text>
      </Box>
    )
  }

  return (
    <Box
      rounded="3xl"
      borderWidth="1px"
      borderColor="ui.border"
      bg="ui.panel"
      px={5}
      py={5}
    >
      <Flex
        justifyContent="space-between"
        gap={3}
        direction={{ base: "column", lg: "row" }}
      >
        <Box>
          <Text fontWeight="bold">{t("validationPanel.title")}</Text>
          <Text mt={1} color="ui.secondaryText">
            {t("validationPanel.readyDescription")}
          </Text>
        </Box>
        <HStack gap={2} alignItems="center">
          {isLoading ? (
            <Badge
              rounded="full"
              bg="ui.brandSoft"
              color="ui.brandText"
              px={3}
              py={1.5}
            >
              <HStack gap={1.5}>
                <Spinner size="xs" color="currentColor" />
                <Text as="span">{t("validationPanel.refreshing")}</Text>
              </HStack>
            </Badge>
          ) : null}
          <Badge
            rounded="full"
            bg="ui.surfaceSoft"
            color="ui.secondaryText"
            px={3}
            py={1.5}
          >
            {t("validationPanel.checkedCount", { count: profiles.length })}
          </Badge>
        </HStack>
      </Flex>

      <Flex mt={4} direction={{ base: "column", lg: "row" }} gap={3}>
        <Box {...countCardStyles.base} {...countCardStyles.brand} flex="1">
          <Text
            fontSize="xs"
            fontWeight="bold"
            textTransform="uppercase"
            letterSpacing="0.08em"
          >
            {t("validationPanel.countCards.ready")}
          </Text>
          <Text mt={1} fontSize="2xl" fontWeight="black">
            {existingProfiles.length}
          </Text>
        </Box>
        <Box {...countCardStyles.base} {...countCardStyles.warning} flex="1">
          <Text
            fontSize="xs"
            fontWeight="bold"
            textTransform="uppercase"
            letterSpacing="0.08em"
          >
            {t("validationPanel.countCards.updateNeeded")}
          </Text>
          <Text mt={1} fontSize="2xl" fontWeight="black">
            {expiredProfiles.length}
          </Text>
        </Box>
        <Box {...countCardStyles.base} {...countCardStyles.danger} flex="1">
          <Text
            fontSize="xs"
            fontWeight="bold"
            textTransform="uppercase"
            letterSpacing="0.08em"
          >
            {t("validationPanel.countCards.missing")}
          </Text>
          <Text mt={1} fontSize="2xl" fontWeight="black">
            {missingProfiles.length}
          </Text>
        </Box>
      </Flex>

      <Flex mt={4} gap={2} wrap="wrap">
        {profiles.map((profile) => {
          const tone = !profile.exists
            ? {
                bg: "ui.dangerSoft",
                borderColor: "ui.danger",
                color: "ui.dangerText",
                icon: FiAlertCircle,
                label: t("validationPanel.status.missing"),
              }
            : profile.expired
              ? {
                  bg: "ui.warningSoft",
                  borderColor: "ui.warning",
                  color: "ui.warningText",
                  icon: FiClock,
                  label: t("validationPanel.status.updateNeeded"),
                }
              : {
                  bg: "ui.brandSoft",
                  borderColor: "ui.brandBorderSoft",
                  color: "ui.brandText",
                  icon: FiCheckCircle,
                  label: t("validationPanel.status.ready"),
                }

          return (
            <Badge
              key={profile.username}
              display="inline-flex"
              alignItems="center"
              gap={1.5}
              rounded="full"
              borderWidth="1px"
              borderColor={tone.borderColor}
              bg={tone.bg}
              color={tone.color}
              px={3}
              py={1.5}
            >
              <Icon as={tone.icon} boxSize={3.5} />@{profile.username} ·{" "}
              {tone.label}
            </Badge>
          )
        })}
      </Flex>

      {error ? (
        <Box
          mt={4}
          rounded="2xl"
          borderWidth="1px"
          borderColor="ui.danger"
          bg="ui.dangerSoft"
          px={4}
          py={4}
        >
          <Text color="ui.dangerText" fontWeight="black">
            {t("validationPanel.refreshFailed")}
          </Text>
          <Text mt={1} color="ui.secondaryText">
            {error}
          </Text>
        </Box>
      ) : null}

      {missingProfiles.length > 0 ? (
        <Box
          mt={4}
          rounded="2xl"
          borderWidth="1px"
          borderColor="ui.danger"
          bg="ui.dangerSoft"
          px={4}
          py={4}
        >
          <Text color="ui.dangerText" fontWeight="black">
            {t("validationPanel.missingBlock")}
          </Text>
        </Box>
      ) : null}
    </Box>
  )
}

export default ProfileValidationPanel
