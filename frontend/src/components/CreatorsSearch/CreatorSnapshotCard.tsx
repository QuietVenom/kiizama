import { Badge, Box, Flex, Grid, Image, Link, Text } from "@chakra-ui/react"
import { FiArrowUpRight, FiEye, FiFileText } from "react-icons/fi"

import type { ProfileSnapshotExpanded } from "@/client"
import { Button } from "@/components/ui/button"

type CreatorSnapshotCardProps = {
  isGeneratingReport?: boolean
  isExpired?: boolean
  onGenerateReport?: () => void
  onOpenDetails: () => void
  snapshot: ProfileSnapshotExpanded
}

const numberFormatter = new Intl.NumberFormat("en-US", {
  notation: "compact",
  maximumFractionDigits: 1,
})

const dateFormatter = new Intl.DateTimeFormat("en-US", {
  day: "2-digit",
  month: "short",
  year: "numeric",
})

const formatNumber = (value?: number | null) => {
  if (typeof value !== "number") {
    return "0"
  }

  return numberFormatter.format(value)
}

const formatDate = (value?: string | null) => {
  if (!value) {
    return "No snapshot date"
  }

  const parsedDate = new Date(value)
  if (Number.isNaN(parsedDate.getTime())) {
    return value
  }

  return dateFormatter.format(parsedDate)
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
  const profile = snapshot.profile
  const categories = profile?.ai_categories?.filter(Boolean) ?? []
  const roles = profile?.ai_roles?.filter(Boolean) ?? []
  const profileImageSrc = profile?.profile_pic_src || profile?.profile_pic_url

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
      <Flex alignItems="flex-start" gap={4}>
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

        <Box minW={0} flex="1">
          <Flex
            alignItems="flex-start"
            justifyContent="space-between"
            gap={3}
            wrap="wrap"
          >
            <Box minW={0}>
              <Text
                fontSize={{ base: "lg", lg: "xl" }}
                fontWeight="black"
                letterSpacing="-0.02em"
                lineClamp={2}
              >
                {profile?.full_name || profile?.username || "Resolved profile"}
              </Text>
              <Text color="ui.link" fontSize="sm" fontWeight="bold">
                @{profile?.username || snapshot.profile_id}
              </Text>
            </Box>

            <Flex alignItems="center" gap={2} wrap="wrap">
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
                  Update Needed
                </Badge>
              ) : null}
              {profile?.is_verified ? (
                <Badge colorPalette="design" rounded="full" px={2.5} py={1}>
                  Verified
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
                  Private
                </Badge>
              ) : null}
            </Flex>
          </Flex>

          <Text
            mt={3}
            color="ui.secondaryText"
            fontSize="sm"
            lineClamp={3}
            minH={{ base: "auto", lg: "60px" }}
          >
            {profile?.biography?.trim() ||
              "No biography available for this creator."}
          </Text>
        </Box>
      </Flex>

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
            Followers
          </Text>
          <Text fontSize="lg" fontWeight="black">
            {formatNumber(profile?.follower_count)}
          </Text>
        </Box>
        <Box>
          <Text color="ui.mutedText" fontSize="xs" fontWeight="bold">
            Following
          </Text>
          <Text fontSize="lg" fontWeight="black">
            {formatNumber(profile?.following_count)}
          </Text>
        </Box>
        <Box>
          <Text color="ui.mutedText" fontSize="xs" fontWeight="bold">
            Media
          </Text>
          <Text fontSize="lg" fontWeight="black">
            {formatNumber(profile?.media_count)}
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
        justifyContent="space-between"
        gap={3}
        borderTopWidth="1px"
        borderTopColor="ui.border"
        pt={5}
        wrap="wrap"
      >
        <Box>
          <Text color="ui.mutedText" fontSize="xs" fontWeight="bold">
            Snapshot captured
          </Text>
          <Text color="ui.secondaryText" fontWeight="semibold">
            {formatDate(snapshot.scraped_at)}
          </Text>
        </Box>

        <Flex alignItems="center" gap={2} wrap="wrap">
          {profile?.username ? (
            <Button
              variant="ghost"
              loading={isGeneratingReport}
              onClick={onGenerateReport}
            >
              <FiFileText />
              Report
            </Button>
          ) : null}
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
              External URL
              <FiArrowUpRight />
            </Link>
          ) : null}

          <Button variant="ghost" onClick={onOpenDetails}>
            <FiEye />
            View detail
          </Button>
        </Flex>
      </Flex>
    </Box>
  )
}

export default CreatorSnapshotCard
