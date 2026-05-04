import {
  Badge,
  Box,
  Flex,
  Image,
  Link,
  SimpleGrid,
  Table,
  Text,
} from "@chakra-ui/react"
import type { ReactNode } from "react"
import { useTranslation } from "react-i18next"
import { FiArrowUpRight } from "react-icons/fi"

import type {
  BioLink,
  PostItem,
  ProfileSnapshotExpanded,
  ReelItem,
} from "@/client"
import { Button } from "@/components/ui/button"
import {
  DialogBody,
  DialogContent,
  DialogFooter,
  DialogHeader,
  DialogRoot,
  DialogTitle,
} from "@/components/ui/dialog"
import { formatDate, formatNumber } from "@/i18n"

type CreatorSnapshotDetailDialogProps = {
  onOpenChange: (open: boolean) => void
  snapshot: ProfileSnapshotExpanded | null
}

type ContentSectionProps = {
  children: ReactNode
  description?: string
  title: string
}

type MetricTileProps = {
  label: string
  value: string
  valueFontSize?: string | { base: string; md: string }
}

type MetricsGroupBoxProps = {
  children: ReactNode
  description?: string
  title: string
}

type PostEntry = {
  item: PostItem
  updatedAt: string
}

type ReelEntry = {
  item: ReelItem
  updatedAt: string
}

const formatSnapshotDateTime = (
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
    month: "long",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  })
}

const formatMetricNumber = (
  value?: number | null,
  language?: string | null,
) => {
  if (typeof value !== "number") {
    return null
  }

  return formatNumber(value, language, {
    maximumFractionDigits: 2,
  })
}

const formatPercent = (value?: number | null, language?: string | null) => {
  if (typeof value !== "number") {
    return null
  }

  return `${formatNumber(value * 100, language, {
    maximumFractionDigits: 2,
  })}%`
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

const getLatestUpdatedAt = (values: Array<{ updated_at: string }>) => {
  return values.reduce<string | undefined>((latest, current) => {
    if (!current.updated_at) {
      return latest
    }

    if (!latest) {
      return current.updated_at
    }

    return new Date(current.updated_at).getTime() > new Date(latest).getTime()
      ? current.updated_at
      : latest
  }, undefined)
}

const flattenPosts = (
  documents: NonNullable<ProfileSnapshotExpanded["posts"]>,
): PostEntry[] =>
  documents.flatMap((document) =>
    (document.posts ?? []).map((item) => ({
      item,
      updatedAt: document.updated_at,
    })),
  )

const flattenReels = (
  documents: NonNullable<ProfileSnapshotExpanded["reels"]>,
): ReelEntry[] =>
  documents.flatMap((document) =>
    (document.reels ?? []).map((item) => ({
      item,
      updatedAt: document.updated_at,
    })),
  )

const getEngagement = (
  likeCount?: number | null,
  commentCount?: number | null,
) => (likeCount ?? 0) + (commentCount ?? 0)

const getPostTypeLabel = (
  mediaType?: number | null,
  productType?: string | null,
  t?: (key: string) => string,
) => {
  if (productType === "clips") {
    return t ? t("detail.types.reel") : "Reel"
  }

  if (productType === "carousel_container" || mediaType === 8) {
    return t ? t("detail.types.carousel") : "Carousel"
  }

  if (mediaType === 2) {
    return t ? t("detail.types.video") : "Video"
  }

  return t ? t("detail.types.post") : "Post"
}

const getReelTypeLabel = (
  mediaType?: number | null,
  productType?: string | null,
  t?: (key: string) => string,
) => {
  if (productType === "clips") {
    return t ? t("detail.types.reel") : "Reel"
  }

  if (mediaType === 2) {
    return t ? t("detail.types.video") : "Video"
  }

  return t ? t("detail.types.reel") : "Reel"
}

const getDisplayUrl = (url?: string | null) => {
  if (!url) {
    return ""
  }

  try {
    return new URL(url).hostname.replace(/^www\./, "")
  } catch {
    return url
  }
}

const formatLinkTitle = (link: BioLink) => {
  const title = link.title?.trim()
  return title || getDisplayUrl(link.url)
}

const ContentSection = ({
  children,
  description,
  title,
}: ContentSectionProps) => (
  <Box
    rounded="3xl"
    borderWidth="1px"
    borderColor="ui.border"
    bg="ui.panel"
    p={{ base: 4, md: 5 }}
  >
    <Text fontSize="sm" fontWeight="black" letterSpacing="0.04em">
      {title}
    </Text>
    {description ? (
      <Text mt={1.5} color="ui.secondaryText" fontSize="sm" maxW="72ch">
        {description}
      </Text>
    ) : null}
    <Box mt={4}>{children}</Box>
  </Box>
)

const MetricTile = ({ label, value, valueFontSize }: MetricTileProps) => (
  <Box
    rounded="2xl"
    borderWidth="1px"
    borderColor="ui.borderSoft"
    bg="ui.surfaceSoft"
    px={4}
    py={4}
  >
    <Text
      color="ui.mutedText"
      fontSize="xs"
      fontWeight="bold"
      letterSpacing="0.08em"
      textTransform="uppercase"
    >
      {label}
    </Text>
    <Text
      mt={2}
      color="ui.text"
      fontSize={valueFontSize ?? { base: "lg", md: "xl" }}
      fontWeight="black"
      lineHeight="1.2"
    >
      {value}
    </Text>
  </Box>
)

const MetricsGroupBox = ({
  children,
  description,
  title,
}: MetricsGroupBoxProps) => (
  <Box
    rounded="2xl"
    borderWidth="1px"
    borderColor="ui.borderSoft"
    bg="ui.surfaceSoft"
    p={{ base: 4, md: 5 }}
  >
    <Text
      color="ui.text"
      fontSize="sm"
      fontWeight="black"
      letterSpacing="0.04em"
    >
      {title}
    </Text>
    {description ? (
      <Text mt={1.5} color="ui.secondaryText" fontSize="sm">
        {description}
      </Text>
    ) : null}
    <SimpleGrid
      mt={4}
      columns={{
        base: 1,
        sm: 2,
      }}
      gap={3}
    >
      {children}
    </SimpleGrid>
  </Box>
)

const CreatorSnapshotDetailDialog = ({
  onOpenChange,
  snapshot,
}: CreatorSnapshotDetailDialogProps) => {
  const { i18n, t } = useTranslation(["creatorsSearch", "common"])
  const profile = snapshot?.profile
  const language = i18n.resolvedLanguage ?? i18n.language
  const profileImageSrc = profile?.profile_pic_src || profile?.profile_pic_url
  const postsDocuments = snapshot?.posts ?? []
  const reelsDocuments = snapshot?.reels ?? []
  const postItems = flattenPosts(postsDocuments)
  const reelItems = flattenReels(reelsDocuments)
  const latestPostsUpdatedAt = getLatestUpdatedAt(postsDocuments)
  const latestReelsUpdatedAt = getLatestUpdatedAt(reelsDocuments)
  const hasPostItems = postItems.length > 0
  const hasReelItems = reelItems.length > 0
  const profileUrl = profile?.username
    ? `https://www.instagram.com/${profile.username}/`
    : undefined
  const categories = profile?.ai_categories?.filter(Boolean) ?? []
  const roles = profile?.ai_roles?.filter(Boolean) ?? []
  const bioLinks = (profile?.bio_links ?? []).filter(
    (link, index, values) =>
      link.url !== profile?.external_url &&
      values.findIndex((candidate) => candidate.url === link.url) === index,
  )

  return (
    <DialogRoot
      open={Boolean(snapshot)}
      placement="center"
      onOpenChange={({ open }) => onOpenChange(open)}
    >
      <DialogContent
        maxW={{ base: "calc(100vw - 1rem)", lg: "1100px" }}
        maxH={{ base: "calc(100vh - 1rem)", lg: "90vh" }}
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
          px={{ base: 5, md: 6 }}
          py={{ base: 5, md: 6 }}
        >
          <DialogTitle
            fontSize={{ base: "xl", md: "2xl" }}
            fontWeight="black"
            letterSpacing="-0.02em"
          >
            {profile?.full_name ||
              profile?.username ||
              t("creatorsSearch:detail.fallbackTitle")}
          </DialogTitle>
          <Text mt={2} color="ui.secondaryText">
            @
            {profile?.username ||
              snapshot?.profile_id ||
              t("creatorsSearch:detail.unknown")}{" "}
            {snapshot
              ? `• ${t("creatorsSearch:detail.snapshotCaptured", {
                  date:
                    formatSnapshotDateTime(snapshot.scraped_at, language) ??
                    t("creatorsSearch:detail.notAvailable"),
                })}`
              : ""}
          </Text>
        </DialogHeader>

        <DialogBody
          px={{ base: 5, md: 6 }}
          py={{ base: 5, md: 6 }}
          overflowY="auto"
        >
          {snapshot ? (
            <Flex direction="column" gap={5}>
              <Box
                layerStyle="dashboardCard"
                p={{ base: 5, md: 6 }}
                bg="ui.panel"
              >
                <Flex gap={4} alignItems="flex-start" wrap="wrap">
                  <Box
                    boxSize={{ base: "18", md: "20" }}
                    flexShrink={0}
                    overflow="hidden"
                    rounded="3xl"
                    borderWidth="1px"
                    borderColor="ui.border"
                    bg="ui.surfaceSoft"
                  >
                    {profileImageSrc ? (
                      <Image
                        alt={
                          profile.username ||
                          t("creatorsSearch:detail.avatarAlt")
                        }
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
                        fontSize="2xl"
                        fontWeight="black"
                      >
                        {getInitials(profile?.full_name, profile?.username)}
                      </Flex>
                    )}
                  </Box>

                  <Box minW={0} flex="1">
                    <Flex alignItems="center" gap={2} wrap="wrap">
                      {profile?.is_verified ? (
                        <Badge
                          colorPalette="design"
                          rounded="full"
                          px={2.5}
                          py={1}
                        >
                          {t("creatorsSearch:card.verified")}
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
                          {t("creatorsSearch:card.private")}
                        </Badge>
                      ) : null}
                    </Flex>

                    <Text
                      mt={3}
                      fontSize={{ base: "xl", md: "2xl" }}
                      fontWeight="black"
                      letterSpacing="-0.02em"
                    >
                      {profile?.full_name ||
                        t("creatorsSearch:detail.noFullName")}
                    </Text>

                    {profileUrl ? (
                      <Link
                        href={profileUrl}
                        target="_blank"
                        rel="noreferrer"
                        color="ui.link"
                        fontWeight="bold"
                        display="inline-flex"
                        alignItems="center"
                        gap={1.5}
                      >
                        @{profile?.username || snapshot.profile_id}
                        <FiArrowUpRight />
                      </Link>
                    ) : (
                      <Text color="ui.link" fontWeight="bold">
                        @{profile?.username || snapshot.profile_id}
                      </Text>
                    )}

                    <Text mt={3} color="ui.secondaryText" lineHeight="1.8">
                      {profile?.biography?.trim() ||
                        t("creatorsSearch:detail.noBiography")}
                    </Text>

                    {profile?.external_url || bioLinks.length > 0 ? (
                      <Flex mt={4} gap={2} wrap="wrap">
                        {profile?.external_url ? (
                          <Link
                            href={profile.external_url}
                            target="_blank"
                            rel="noreferrer"
                            display="inline-flex"
                            alignItems="center"
                            gap={1.5}
                            rounded="full"
                            borderWidth="1px"
                            borderColor="ui.borderSoft"
                            bg="ui.surfaceSoft"
                            px={3}
                            py={1.5}
                            color="ui.link"
                            fontSize="sm"
                            fontWeight="bold"
                          >
                            {getDisplayUrl(profile.external_url)}
                            <FiArrowUpRight />
                          </Link>
                        ) : null}
                        {bioLinks.map((link) => (
                          <Link
                            key={`${link.url}-${link.title}`}
                            href={link.url}
                            target="_blank"
                            rel="noreferrer"
                            display="inline-flex"
                            alignItems="center"
                            gap={1.5}
                            rounded="full"
                            borderWidth="1px"
                            borderColor="ui.borderSoft"
                            bg="ui.surfaceSoft"
                            px={3}
                            py={1.5}
                            color="ui.secondaryText"
                            fontSize="sm"
                            fontWeight="semibold"
                            maxW="full"
                          >
                            <Text truncate>{formatLinkTitle(link)}</Text>
                            <FiArrowUpRight />
                          </Link>
                        ))}
                      </Flex>
                    ) : null}
                  </Box>
                </Flex>
              </Box>

              <SimpleGrid columns={{ base: 1, md: 3 }} gap={4}>
                <MetricTile
                  label={t("creatorsSearch:detail.followers")}
                  value={
                    formatMetricNumber(profile?.follower_count, language) ??
                    t("creatorsSearch:detail.notAvailable")
                  }
                />
                <MetricTile
                  label={t("creatorsSearch:detail.following")}
                  value={
                    formatMetricNumber(profile?.following_count, language) ??
                    t("creatorsSearch:detail.notAvailable")
                  }
                />
                <MetricTile
                  label={t("creatorsSearch:detail.media")}
                  value={
                    formatMetricNumber(profile?.media_count, language) ??
                    t("creatorsSearch:detail.notAvailable")
                  }
                />
              </SimpleGrid>

              <ContentSection
                title={t("creatorsSearch:detail.analysis.title")}
                description={t("creatorsSearch:detail.analysis.description")}
              >
                <SimpleGrid columns={{ base: 1, lg: 2 }} gap={4}>
                  <Box
                    rounded="2xl"
                    borderWidth="1px"
                    borderColor="ui.borderSoft"
                    bg="ui.surfaceSoft"
                    px={4}
                    py={4}
                  >
                    <Text
                      color="ui.mutedText"
                      fontSize="xs"
                      fontWeight="bold"
                      letterSpacing="0.08em"
                      textTransform="uppercase"
                    >
                      {t("creatorsSearch:detail.analysis.categories")}
                    </Text>
                    <Flex mt={3} gap={2} wrap="wrap">
                      {categories.length > 0 ? (
                        categories.map((category) => (
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
                        ))
                      ) : (
                        <Text color="ui.secondaryText" fontSize="sm">
                          {t("creatorsSearch:detail.analysis.noCategories")}
                        </Text>
                      )}
                    </Flex>
                  </Box>

                  <Box
                    rounded="2xl"
                    borderWidth="1px"
                    borderColor="ui.borderSoft"
                    bg="ui.surfaceSoft"
                    px={4}
                    py={4}
                  >
                    <Text
                      color="ui.mutedText"
                      fontSize="xs"
                      fontWeight="bold"
                      letterSpacing="0.08em"
                      textTransform="uppercase"
                    >
                      {t("creatorsSearch:detail.analysis.roles")}
                    </Text>
                    <Flex mt={3} gap={2} wrap="wrap">
                      {roles.length > 0 ? (
                        roles.map((role) => (
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
                        ))
                      ) : (
                        <Text color="ui.secondaryText" fontSize="sm">
                          {t("creatorsSearch:detail.analysis.noRoles")}
                        </Text>
                      )}
                    </Flex>
                  </Box>
                </SimpleGrid>
              </ContentSection>

              <ContentSection
                title={t("creatorsSearch:detail.metrics.title")}
                description={t("creatorsSearch:detail.metrics.description")}
              >
                {snapshot.metrics && (hasPostItems || hasReelItems) ? (
                  <SimpleGrid
                    columns={{
                      base: 1,
                      xl: hasPostItems && hasReelItems ? 2 : 1,
                    }}
                    gap={4}
                  >
                    {hasPostItems ? (
                      <MetricsGroupBox
                        title={t("creatorsSearch:detail.metrics.postsTitle")}
                        description={t(
                          "creatorsSearch:detail.metrics.postsDescription",
                          { count: postItems.length },
                        )}
                      >
                        <MetricTile
                          label={t(
                            "creatorsSearch:detail.metrics.tiles.totalPosts",
                          )}
                          value={
                            formatMetricNumber(
                              snapshot.metrics.post_metrics.total_posts,
                              language,
                            ) ?? t("creatorsSearch:detail.notAvailable")
                          }
                        />
                        <MetricTile
                          label={t(
                            "creatorsSearch:detail.metrics.tiles.overallPostEr",
                          )}
                          value={
                            formatPercent(
                              snapshot.metrics.overall_post_engagement_rate,
                              language,
                            ) ?? t("creatorsSearch:detail.notAvailable")
                          }
                        />
                        <MetricTile
                          label={t(
                            "creatorsSearch:detail.metrics.tiles.totalPostLikes",
                          )}
                          value={
                            formatMetricNumber(
                              snapshot.metrics.post_metrics.total_likes,
                              language,
                            ) ?? t("creatorsSearch:detail.notAvailable")
                          }
                        />
                        <MetricTile
                          label={t(
                            "creatorsSearch:detail.metrics.tiles.totalPostComments",
                          )}
                          value={
                            formatMetricNumber(
                              snapshot.metrics.post_metrics.total_comments,
                              language,
                            ) ?? t("creatorsSearch:detail.notAvailable")
                          }
                        />
                        <MetricTile
                          label={t(
                            "creatorsSearch:detail.metrics.tiles.avgPostLikes",
                          )}
                          value={
                            formatMetricNumber(
                              snapshot.metrics.post_metrics.avg_likes,
                              language,
                            ) ?? t("creatorsSearch:detail.notAvailable")
                          }
                        />
                        <MetricTile
                          label={t(
                            "creatorsSearch:detail.metrics.tiles.avgPostComments",
                          )}
                          value={
                            formatMetricNumber(
                              snapshot.metrics.post_metrics.avg_comments,
                              language,
                            ) ?? t("creatorsSearch:detail.notAvailable")
                          }
                        />
                        <MetricTile
                          label={t(
                            "creatorsSearch:detail.metrics.tiles.avgPostEr",
                          )}
                          value={
                            formatPercent(
                              snapshot.metrics.post_metrics.avg_engagement_rate,
                              language,
                            ) ?? t("creatorsSearch:detail.notAvailable")
                          }
                        />
                        <MetricTile
                          label={t(
                            "creatorsSearch:detail.metrics.tiles.hashtagsPerPost",
                          )}
                          value={
                            formatMetricNumber(
                              snapshot.metrics.post_metrics.hashtags_per_post,
                              language,
                            ) ?? t("creatorsSearch:detail.notAvailable")
                          }
                        />
                        <MetricTile
                          label={t(
                            "creatorsSearch:detail.metrics.tiles.mentionsPerPost",
                          )}
                          value={
                            formatMetricNumber(
                              snapshot.metrics.post_metrics.mentions_per_post,
                              language,
                            ) ?? t("creatorsSearch:detail.notAvailable")
                          }
                        />
                      </MetricsGroupBox>
                    ) : null}

                    {hasReelItems ? (
                      <MetricsGroupBox
                        title={t("creatorsSearch:detail.metrics.reelsTitle")}
                        description={t(
                          "creatorsSearch:detail.metrics.reelsDescription",
                          { count: reelItems.length },
                        )}
                      >
                        <MetricTile
                          label={t(
                            "creatorsSearch:detail.metrics.tiles.totalReels",
                          )}
                          value={
                            formatMetricNumber(
                              snapshot.metrics.reel_metrics.total_reels,
                              language,
                            ) ?? t("creatorsSearch:detail.notAvailable")
                          }
                        />
                        <MetricTile
                          label={t(
                            "creatorsSearch:detail.metrics.tiles.reelErOnPlays",
                          )}
                          value={
                            formatPercent(
                              snapshot.metrics.reel_engagement_rate_on_plays,
                              language,
                            ) ?? t("creatorsSearch:detail.notAvailable")
                          }
                        />
                        <MetricTile
                          label={t(
                            "creatorsSearch:detail.metrics.tiles.totalPlays",
                          )}
                          value={
                            formatMetricNumber(
                              snapshot.metrics.reel_metrics.total_plays,
                              language,
                            ) ?? t("creatorsSearch:detail.notAvailable")
                          }
                        />
                        <MetricTile
                          label={t(
                            "creatorsSearch:detail.metrics.tiles.avgReelPlays",
                          )}
                          value={
                            formatMetricNumber(
                              snapshot.metrics.reel_metrics.avg_plays,
                              language,
                            ) ?? t("creatorsSearch:detail.notAvailable")
                          }
                        />
                        <MetricTile
                          label={t(
                            "creatorsSearch:detail.metrics.tiles.avgReelLikes",
                          )}
                          value={
                            formatMetricNumber(
                              snapshot.metrics.reel_metrics.avg_reel_likes,
                              language,
                            ) ?? t("creatorsSearch:detail.notAvailable")
                          }
                        />
                        <MetricTile
                          label={t(
                            "creatorsSearch:detail.metrics.tiles.avgReelComments",
                          )}
                          value={
                            formatMetricNumber(
                              snapshot.metrics.reel_metrics.avg_reel_comments,
                              language,
                            ) ?? t("creatorsSearch:detail.notAvailable")
                          }
                        />
                      </MetricsGroupBox>
                    ) : null}
                  </SimpleGrid>
                ) : (
                  <Text color="ui.secondaryText">
                    {t("creatorsSearch:detail.metrics.empty")}
                  </Text>
                )}
              </ContentSection>

              {hasPostItems ? (
                <ContentSection
                  title={t("creatorsSearch:detail.posts.title", {
                    count: postItems.length,
                  })}
                  description={t("creatorsSearch:detail.posts.description", {
                    count: postsDocuments.length,
                    date:
                      formatSnapshotDateTime(latestPostsUpdatedAt, language) ??
                      t("creatorsSearch:detail.unknown"),
                  })}
                >
                  <Box overflowX="auto">
                    <Table.Root size={{ base: "sm", md: "md" }} minW="920px">
                      <Table.Header>
                        <Table.Row>
                          <Table.ColumnHeader>
                            {t("creatorsSearch:detail.posts.table.post")}
                          </Table.ColumnHeader>
                          <Table.ColumnHeader>
                            {t("creatorsSearch:detail.posts.table.likes")}
                          </Table.ColumnHeader>
                          <Table.ColumnHeader>
                            {t("creatorsSearch:detail.posts.table.comments")}
                          </Table.ColumnHeader>
                          <Table.ColumnHeader>
                            {t("creatorsSearch:detail.posts.table.engagement")}
                          </Table.ColumnHeader>
                          <Table.ColumnHeader>
                            {t("creatorsSearch:detail.posts.table.erFollowers")}
                          </Table.ColumnHeader>
                          <Table.ColumnHeader>
                            {t("creatorsSearch:detail.posts.table.colabs")}
                          </Table.ColumnHeader>
                          <Table.ColumnHeader>
                            {t("creatorsSearch:detail.posts.table.usertags")}
                          </Table.ColumnHeader>
                          <Table.ColumnHeader>
                            {t("creatorsSearch:detail.posts.table.type")}
                          </Table.ColumnHeader>
                        </Table.Row>
                      </Table.Header>
                      <Table.Body>
                        {postItems.map(({ item, updatedAt }, index) => {
                          const engagement = getEngagement(
                            item.like_count,
                            item.comment_count,
                          )
                          const postEr =
                            typeof profile?.follower_count === "number" &&
                            profile.follower_count > 0
                              ? engagement / profile.follower_count
                              : null

                          return (
                            <Table.Row
                              key={`${item.code}-${updatedAt}-${index}`}
                            >
                              <Table.Cell>
                                <Flex alignItems="flex-start" gap={3}>
                                  <Link
                                    href={`https://www.instagram.com/p/${item.code}/`}
                                    target="_blank"
                                    rel="noreferrer"
                                    display="inline-flex"
                                    alignItems="center"
                                    justifyContent="center"
                                    boxSize="9"
                                    flexShrink={0}
                                    rounded="xl"
                                    borderWidth="1px"
                                    borderColor="ui.borderSoft"
                                    bg="ui.surfaceSoft"
                                    color="ui.link"
                                  >
                                    <FiArrowUpRight />
                                  </Link>
                                  <Box minW={0}>
                                    <Text fontWeight="bold" lineClamp={2}>
                                      {item.caption_text?.trim() ||
                                        t(
                                          "creatorsSearch:detail.posts.fallbackTitle",
                                          {
                                            count: index + 1,
                                          },
                                        )}
                                    </Text>
                                    <Text
                                      mt={1}
                                      color="ui.secondaryText"
                                      fontSize="xs"
                                    >
                                      {t(
                                        "creatorsSearch:detail.posts.updatedCode",
                                        {
                                          code: item.code,
                                          date:
                                            formatSnapshotDateTime(
                                              updatedAt,
                                              language,
                                            ) ??
                                            t("creatorsSearch:detail.unknown"),
                                        },
                                      )}
                                    </Text>
                                    {item.is_paid_partnership ? (
                                      <Badge
                                        mt={2}
                                        rounded="full"
                                        bg="ui.brandSoft"
                                        color="ui.brandText"
                                        px={2.5}
                                        py={1}
                                      >
                                        {t(
                                          "creatorsSearch:detail.posts.paidPartnership",
                                        )}
                                      </Badge>
                                    ) : null}
                                  </Box>
                                </Flex>
                              </Table.Cell>
                              <Table.Cell>
                                {formatMetricNumber(
                                  item.like_count ?? 0,
                                  language,
                                ) ?? "0"}
                              </Table.Cell>
                              <Table.Cell>
                                {formatMetricNumber(
                                  item.comment_count ?? 0,
                                  language,
                                ) ?? "0"}
                              </Table.Cell>
                              <Table.Cell>
                                {formatMetricNumber(engagement, language) ??
                                  "0"}
                              </Table.Cell>
                              <Table.Cell>
                                {formatPercent(postEr, language) ??
                                  t("creatorsSearch:detail.notAvailable")}
                              </Table.Cell>
                              <Table.Cell>
                                <Text fontWeight="bold">
                                  {formatMetricNumber(
                                    item.coauthor_producers?.length ?? 0,
                                    language,
                                  ) ?? "0"}
                                </Text>
                                {item.coauthor_producers?.length ? (
                                  <Text
                                    mt={1}
                                    color="ui.secondaryText"
                                    fontSize="xs"
                                    lineClamp={2}
                                  >
                                    {item.coauthor_producers
                                      .map((author) => `@${author}`)
                                      .join(", ")}
                                  </Text>
                                ) : null}
                              </Table.Cell>
                              <Table.Cell>
                                <Text fontWeight="bold">
                                  {formatMetricNumber(
                                    item.usertags?.length ?? 0,
                                    language,
                                  ) ?? "0"}
                                </Text>
                                {item.usertags?.length ? (
                                  <Text
                                    mt={1}
                                    color="ui.secondaryText"
                                    fontSize="xs"
                                    lineClamp={2}
                                  >
                                    {item.usertags
                                      .map((tag) => `@${tag}`)
                                      .join(", ")}
                                  </Text>
                                ) : null}
                              </Table.Cell>
                              <Table.Cell>
                                {getPostTypeLabel(
                                  item.media_type,
                                  item.product_type,
                                  (key) => t(`creatorsSearch:${key}`),
                                )}
                              </Table.Cell>
                            </Table.Row>
                          )
                        })}
                      </Table.Body>
                    </Table.Root>
                  </Box>
                </ContentSection>
              ) : null}

              {hasReelItems ? (
                <ContentSection
                  title={t("creatorsSearch:detail.reels.title", {
                    count: reelItems.length,
                  })}
                  description={t("creatorsSearch:detail.reels.description", {
                    count: reelsDocuments.length,
                    date:
                      formatSnapshotDateTime(latestReelsUpdatedAt, language) ??
                      t("creatorsSearch:detail.unknown"),
                  })}
                >
                  <Box overflowX="auto">
                    <Table.Root size={{ base: "sm", md: "md" }} minW="860px">
                      <Table.Header>
                        <Table.Row>
                          <Table.ColumnHeader>
                            {t("creatorsSearch:detail.reels.table.reel")}
                          </Table.ColumnHeader>
                          <Table.ColumnHeader>
                            {t("creatorsSearch:detail.reels.table.plays")}
                          </Table.ColumnHeader>
                          <Table.ColumnHeader>
                            {t("creatorsSearch:detail.reels.table.likes")}
                          </Table.ColumnHeader>
                          <Table.ColumnHeader>
                            {t("creatorsSearch:detail.reels.table.comments")}
                          </Table.ColumnHeader>
                          <Table.ColumnHeader>
                            {t("creatorsSearch:detail.reels.table.engagement")}
                          </Table.ColumnHeader>
                          <Table.ColumnHeader>
                            {t("creatorsSearch:detail.reels.table.erPlays")}
                          </Table.ColumnHeader>
                          <Table.ColumnHeader>
                            {t("creatorsSearch:detail.reels.table.type")}
                          </Table.ColumnHeader>
                        </Table.Row>
                      </Table.Header>
                      <Table.Body>
                        {reelItems.map(({ item, updatedAt }, index) => {
                          const engagement = getEngagement(
                            item.like_count,
                            item.comment_count,
                          )
                          const reelEr =
                            typeof item.play_count === "number" &&
                            item.play_count > 0
                              ? engagement / item.play_count
                              : null

                          return (
                            <Table.Row
                              key={`${item.code}-${updatedAt}-${index}`}
                            >
                              <Table.Cell>
                                <Flex alignItems="flex-start" gap={3}>
                                  <Link
                                    href={`https://www.instagram.com/reel/${item.code}/`}
                                    target="_blank"
                                    rel="noreferrer"
                                    display="inline-flex"
                                    alignItems="center"
                                    justifyContent="center"
                                    boxSize="9"
                                    flexShrink={0}
                                    rounded="xl"
                                    borderWidth="1px"
                                    borderColor="ui.borderSoft"
                                    bg="ui.surfaceSoft"
                                    color="ui.link"
                                  >
                                    <FiArrowUpRight />
                                  </Link>
                                  <Box minW={0}>
                                    <Text fontWeight="bold">
                                      {t(
                                        "creatorsSearch:detail.reels.fallbackTitle",
                                        {
                                          count: index + 1,
                                        },
                                      )}
                                    </Text>
                                    <Text
                                      mt={1}
                                      color="ui.secondaryText"
                                      fontSize="xs"
                                    >
                                      {t(
                                        "creatorsSearch:detail.reels.updatedCode",
                                        {
                                          code: item.code,
                                          date:
                                            formatSnapshotDateTime(
                                              updatedAt,
                                              language,
                                            ) ??
                                            t("creatorsSearch:detail.unknown"),
                                        },
                                      )}
                                    </Text>
                                  </Box>
                                </Flex>
                              </Table.Cell>
                              <Table.Cell>
                                {formatMetricNumber(
                                  item.play_count ?? 0,
                                  language,
                                ) ?? "0"}
                              </Table.Cell>
                              <Table.Cell>
                                {formatMetricNumber(
                                  item.like_count ?? 0,
                                  language,
                                ) ?? "0"}
                              </Table.Cell>
                              <Table.Cell>
                                {formatMetricNumber(
                                  item.comment_count ?? 0,
                                  language,
                                ) ?? "0"}
                              </Table.Cell>
                              <Table.Cell>
                                {formatMetricNumber(engagement, language) ??
                                  "0"}
                              </Table.Cell>
                              <Table.Cell>
                                {formatPercent(reelEr, language) ??
                                  t("creatorsSearch:detail.notAvailable")}
                              </Table.Cell>
                              <Table.Cell>
                                {getReelTypeLabel(
                                  item.media_type,
                                  item.product_type,
                                  (key) => t(`creatorsSearch:${key}`),
                                )}
                              </Table.Cell>
                            </Table.Row>
                          )
                        })}
                      </Table.Body>
                    </Table.Root>
                  </Box>
                </ContentSection>
              ) : null}
            </Flex>
          ) : null}
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

export default CreatorSnapshotDetailDialog
