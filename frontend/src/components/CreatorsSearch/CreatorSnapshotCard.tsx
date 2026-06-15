import { Badge, Box, Flex, Grid, Image, Link, Text } from "@chakra-ui/react"
import { useTranslation } from "react-i18next"
import { FiArrowUpRight, FiEye, FiFileText } from "react-icons/fi"

import type { ProfileSnapshotExpanded } from "@/client"
import { Button } from "@/components/ui/button"
import { formatDate, getLocaleForLanguage } from "@/i18n"

type CreatorSnapshotCardProps = {
  isGeneratingReport?: boolean
  isExpired?: boolean
  onGenerateReport?: () => void
  onOpenDetails: () => void
  snapshot: ProfileSnapshotExpanded
}

const formatCompactNumber = (
  value: number | null | undefined,
  language?: string | null,
) => {
  if (typeof value !== "number") {
    return "0"
  }

  return new Intl.NumberFormat(getLocaleForLanguage(language), {
    notation: "compact",
    maximumFractionDigits: 1,
  }).format(value)
}

const formatSnapshotDate = (
  value?: string | null,
  language?: string | null,
) => {
  if (!value) {
    return null
  }

  const parsedDate = new Date(value)
  if (Number.isNaN(parsedDate.getTime())) {
    return value
  }

  return formatDate(parsedDate, language, {
    day: "2-digit",
    month: "short",
    year: "numeric",
  })
}

const getInitials = (fullName?: string | null, username?: string | null) => {
  const source = fullName?.trim() || username?.trim() || "Creator"
  return source
    .split(/\s+/)
    .filter(Boolean)
    .slice(0, 2)
    .map((part) => part[0]?.toUpperCase())
    .join("")
}

const CreatorSnapshotCard = ({
  isGeneratingReport = false,
  isExpired = false,
  onGenerateReport,
  onOpenDetails,
  snapshot,
}: CreatorSnapshotCardProps) => {
  const { i18n, t } = useTranslation("creatorsSearch")
  const profile = snapshot.profile
  const categories = profile?.ai_categories?.filter(Boolean) ?? []
  const roles = profile?.ai_roles?.filter(Boolean) ?? []
  const profileImageSrc = profile?.profile_pic_src || profile?.profile_pic_url

  const language = i18n.resolvedLanguage ?? i18n.language

  return (
    <Box
      layerStyle="dashboardCardInteractive"
      display="flex"
      h="full"
      flexDirection="column"
      p={{ base: 5, lg: 6 }}
      borderColor={isExpired ? "ui.warning" : undefined}
      bg={isExpired ? "ui.warningSoft" : undefined}
    >
      <Grid templateColumns="auto 1fr" gap={4} alignItems="start">
        <Box
          boxSize={{ base: "16", lg: "18" }}
          flexShrink={0}
          overflow="hidden"
          rounded="3xl"
          borderWidth="1px"
          borderColor="ui.border"
          bg="ui.surfaceSoft"
        >
          {profileImageSrc ? (
            <Image
              alt={profile.username}
              h="full"
              src={profileImageSrc}
              w="full"
              objectFit="cover"
            />
          ) : (
            <Flex
              h="full"
              alignItems="center"
              justifyContent="center"
              bg="ui.brandGlow"
              color="ui.brandText"
              fontSize="xl"
              fontWeight="black"
            >
              {getInitials(profile?.full_name, profile?.username)}
            </Flex>
          )}
        </Box>

        <Flex
          gridColumn="2"
          flexShrink={0}
          alignItems="center"
          gap={2}
          wrap="wrap"
          justifyContent="flex-end"
          minW={0}
        >
          {profile?.username ? (
            <Button
              variant="ghost"
              loading={isGeneratingReport}
              onClick={onGenerateReport}
            >
              <FiFileText />
              {t("card.report")}
            </Button>
          ) : null}
          <Button variant="ghost" onClick={onOpenDetails}>
            <FiEye />
            {t("card.viewDetail")}
          </Button>
        </Flex>

        <Box gridColumn="1 / -1" minW={0}>
          <Text
            fontSize={{ base: "lg", lg: "xl" }}
            fontWeight="black"
            letterSpacing="-0.02em"
            lineClamp={2}
          >
            {profile?.full_name || profile?.username || t("card.fallbackName")}
          </Text>
          <Flex mt={1.5} alignItems="center" gap={2} wrap="wrap">
            <Text color="ui.link" fontSize="sm" fontWeight="bold">
              @{profile?.username || snapshot.profile_id}
            </Text>
            {isExpired ? (
              <Badge
                rounded="full"
                borderWidth="1px"
                borderColor="ui.warning"
                bg="ui.panel"
                color="ui.warningText"
                px={2.5}
                py={1}
              >
                {t("card.updateNeeded")}
              </Badge>
            ) : null}
            {profile?.is_verified ? (
              <Badge colorPalette="design" rounded="full" px={2.5} py={1}>
                {t("card.verified")}
              </Badge>
            ) : null}
            {profile?.is_private ? (
              <Badge
                rounded="full"
                borderWidth="1px"
                borderColor="ui.borderSoft"
                bg="ui.surfaceSoft"
                color="ui.secondaryText"
                px={2.5}
                py={1}
              >
                {t("card.private")}
              </Badge>
            ) : null}
          </Flex>
          <Text
            mt={3}
            color="ui.secondaryText"
            fontSize="sm"
            lineClamp={3}
            minH={{ base: "auto", lg: "60px" }}
          >
            {profile?.biography?.trim() || t("card.noBiography")}
          </Text>
        </Box>
      </Grid>

      <Grid
        mt={5}
        templateColumns="repeat(3, minmax(0, 1fr))"
        gap={3}
        borderTopWidth="1px"
        borderTopColor="ui.border"
        pt={5}
      >
        <Box>
          <Text color="ui.mutedText" fontSize="xs" fontWeight="bold">
            {t("card.followers")}
          </Text>
          <Text fontSize="lg" fontWeight="black">
            {formatCompactNumber(profile?.follower_count, language)}
          </Text>
        </Box>
        <Box>
          <Text color="ui.mutedText" fontSize="xs" fontWeight="bold">
            {t("card.following")}
          </Text>
          <Text fontSize="lg" fontWeight="black">
            {formatCompactNumber(profile?.following_count, language)}
          </Text>
        </Box>
        <Box>
          <Text color="ui.mutedText" fontSize="xs" fontWeight="bold">
            {t("card.media")}
          </Text>
          <Text fontSize="lg" fontWeight="black">
            {formatCompactNumber(profile?.media_count, language)}
          </Text>
        </Box>
      </Grid>

      {categories.length > 0 || roles.length > 0 ? (
        <Flex mt={4} gap={2} wrap="wrap">
          {categories.map((category) => (
            <Badge
              key={`category-${category}`}
              rounded="full"
              bg="ui.infoSoft"
              color="ui.infoText"
              px={2.5}
              py={1}
            >
              {category}
            </Badge>
          ))}
          {roles.map((role) => (
            <Badge
              key={`role-${role}`}
              rounded="full"
              bg="ui.accentSoft"
              color="ui.accentText"
              px={2.5}
              py={1}
            >
              {role}
            </Badge>
          ))}
        </Flex>
      ) : null}

      <Flex
        mt={5}
        alignItems="center"
        justifyContent="flex-end"
        gap={3}
        borderTopWidth="1px"
        borderTopColor="ui.border"
        pt={5}
        wrap="wrap"
      >
        <Flex alignItems="center" gap={3} wrap="wrap">
          <Text color="ui.secondaryText" fontSize="sm" fontWeight="semibold">
            {formatSnapshotDate(snapshot.scraped_at, language) ??
              t("card.noSnapshotDate")}
          </Text>
          {profile?.external_url ? (
            <Link
              href={profile.external_url}
              target="_blank"
              rel="noreferrer"
              color="ui.secondaryText"
              fontSize="sm"
              fontWeight="semibold"
              display="inline-flex"
              alignItems="center"
              gap={1.5}
              _hover={{ color: "ui.link" }}
            >
              {t("card.externalUrl")}
              <FiArrowUpRight />
            </Link>
          ) : null}
        </Flex>
      </Flex>
    </Box>
  )
}

export default CreatorSnapshotCard
