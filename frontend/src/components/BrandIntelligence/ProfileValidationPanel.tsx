import { Badge, Box, Flex, HStack, Icon, Spinner, Text } from "@chakra-ui/react"
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
        <Text fontWeight="bold">Profile validation gate</Text>
        <Text mt={2} color="ui.secondaryText">
          Add the required influencer usernames first to enable validation and
          the rest of the workflow.
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
              Validating profiles
            </Text>
            <Text mt={1} color="ui.secondaryText">
              Checking whether these usernames already exist in Mining.
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
              Validation failed
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
              Validation is outdated
            </Text>
            <Text mt={1} color="ui.secondaryText">
              Usernames changed after the last check. Validate again before
              generating the report.
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
        <Text fontWeight="bold">Profile validation gate</Text>
        <Text mt={2} color="ui.secondaryText">
          Run profile validation before report generation. This step is always
          required before any strategy endpoint.
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
          <Text fontWeight="bold">Profile validation gate</Text>
          <Text mt={1} color="ui.secondaryText">
            Existing profiles can continue. Profiles marked as update needed can
            also continue, but missing usernames block report generation.
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
                <Text as="span">Refreshing</Text>
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
            {profiles.length} checked
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
            Ready
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
            Update Needed
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
            Missing
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
                label: "Missing",
              }
            : profile.expired
              ? {
                  bg: "ui.warningSoft",
                  borderColor: "ui.warning",
                  color: "ui.warningText",
                  icon: FiClock,
                  label: "Update Needed",
                }
              : {
                  bg: "ui.brandSoft",
                  borderColor: "ui.brandBorderSoft",
                  color: "ui.brandText",
                  icon: FiCheckCircle,
                  label: "Ready",
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
            Validation refresh failed
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
            consulte los perfiles en Mining y vuelva a intentar
          </Text>
        </Box>
      ) : null}
    </Box>
  )
}

export default ProfileValidationPanel
