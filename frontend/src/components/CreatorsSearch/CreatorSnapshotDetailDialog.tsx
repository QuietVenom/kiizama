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

type PostEntry = {
  item: PostItem
  updatedAt: string
}

type ReelEntry = {
  item: ReelItem
  updatedAt: string
}

const dateFormatter = new Intl.DateTimeFormat("en-US", {
  day: "2-digit",
  month: "long",
  year: "numeric",
  hour: "2-digit",
  minute: "2-digit",
})

const numberFormatter = new Intl.NumberFormat("en-US", {
  maximumFractionDigits: 2,
})

const formatDate = (value?: string | null) => {
  if (!value) {
    return "N/A"
  }

  const parsedDate = new Date(value)
  if (Number.isNaN(parsedDate.getTime())) {
    return value
  }

  return dateFormatter.format(parsedDate)
}

const formatNumber = (value?: number | null) => {
  if (typeof value !== "number") {
    return "N/A"
  }

  return numberFormatter.format(value)
}

const formatPercent = (value?: number | null) => {
  if (typeof value !== "number") {
    return "N/A"
  }

  return `${numberFormatter.format(value * 100)}%`
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
) => {
  if (productType === "clips") {
    return "Reel"
  }

  if (productType === "carousel_container" || mediaType === 8) {
    return "Carousel"
  }

  if (mediaType === 2) {
    return "Video"
  }

  return "Post"
}

const getReelTypeLabel = (
  mediaType?: number | null,
  productType?: string | null,
) => {
  if (productType === "clips") {
    return "Reel"
  }

  if (mediaType === 2) {
    return "Video"
  }

  return "Reel"
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

const CreatorSnapshotDetailDialog = ({
  onOpenChange,
  snapshot,
}: CreatorSnapshotDetailDialogProps) => {
  const profile = snapshot?.profile
  const profileImageSrc = profile?.profile_pic_src || profile?.profile_pic_url
  const postsDocuments = snapshot?.posts ?? []
  const reelsDocuments = snapshot?.reels ?? []
  const postItems = flattenPosts(postsDocuments)
  const reelItems = flattenReels(reelsDocuments)
  const latestPostsUpdatedAt = getLatestUpdatedAt(postsDocuments)
  const latestReelsUpdatedAt = getLatestUpdatedAt(reelsDocuments)
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
              "Creator snapshot detail"}
          </DialogTitle>
          <Text mt={2} color="ui.secondaryText">
            @{profile?.username || snapshot?.profile_id || "unknown"}{" "}
            {snapshot
              ? `• Snapshot captured ${formatDate(snapshot.scraped_at)}`
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
                        alt={profile.username || "Creator avatar"}
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

                    <Text
                      mt={3}
                      fontSize={{ base: "xl", md: "2xl" }}
                      fontWeight="black"
                      letterSpacing="-0.02em"
                    >
                      {profile?.full_name || "No full name"}
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
                      {profile?.biography?.trim() || "No biography available."}
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
                  label="Followers"
                  value={formatNumber(profile?.follower_count)}
                />
                <MetricTile
                  label="Following"
                  value={formatNumber(profile?.following_count)}
                />
                <MetricTile
                  label="Media"
                  value={formatNumber(profile?.media_count)}
                />
              </SimpleGrid>

              <ContentSection
                title="AI analysis"
                description="Saved content categories and creator roles associated with this profile."
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
                      Categories
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
                          No categories available.
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
                      Roles
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
                          No roles available.
                        </Text>
                      )}
                    </Flex>
                  </Box>
                </SimpleGrid>
              </ContentSection>

              <ContentSection
                title="Metrics"
                description="Saved creator metrics arranged to match the report view used across the product."
              >
                {snapshot.metrics ? (
                  <SimpleGrid
                    columns={{
                      base: 1,
                      sm: 2,
                      xl: 3,
                    }}
                    gap={3}
                  >
                    <MetricTile
                      label="Total posts"
                      value={formatNumber(
                        snapshot.metrics.post_metrics.total_posts,
                      )}
                    />
                    <MetricTile
                      label="Total post likes"
                      value={formatNumber(
                        snapshot.metrics.post_metrics.total_likes,
                      )}
                    />
                    <MetricTile
                      label="Total post comments"
                      value={formatNumber(
                        snapshot.metrics.post_metrics.total_comments,
                      )}
                    />
                    <MetricTile
                      label="Avg post likes"
                      value={formatNumber(
                        snapshot.metrics.post_metrics.avg_likes,
                      )}
                    />
                    <MetricTile
                      label="Avg post comments"
                      value={formatNumber(
                        snapshot.metrics.post_metrics.avg_comments,
                      )}
                    />
                    <MetricTile
                      label="Avg post ER"
                      value={formatPercent(
                        snapshot.metrics.post_metrics.avg_engagement_rate,
                      )}
                    />
                    <MetricTile
                      label="Hashtags per post"
                      value={formatNumber(
                        snapshot.metrics.post_metrics.hashtags_per_post,
                      )}
                    />
                    <MetricTile
                      label="Mentions per post"
                      value={formatNumber(
                        snapshot.metrics.post_metrics.mentions_per_post,
                      )}
                    />
                    <MetricTile
                      label="Total reels"
                      value={formatNumber(
                        snapshot.metrics.reel_metrics.total_reels,
                      )}
                    />
                    <MetricTile
                      label="Total plays"
                      value={formatNumber(
                        snapshot.metrics.reel_metrics.total_plays,
                      )}
                    />
                    <MetricTile
                      label="Avg reel plays"
                      value={formatNumber(
                        snapshot.metrics.reel_metrics.avg_plays,
                      )}
                    />
                    <MetricTile
                      label="Avg reel likes"
                      value={formatNumber(
                        snapshot.metrics.reel_metrics.avg_reel_likes,
                      )}
                    />
                    <MetricTile
                      label="Avg reel comments"
                      value={formatNumber(
                        snapshot.metrics.reel_metrics.avg_reel_comments,
                      )}
                    />
                    <MetricTile
                      label="Overall engagement rate"
                      value={formatPercent(
                        snapshot.metrics.overall_engagement_rate,
                      )}
                    />
                  </SimpleGrid>
                ) : (
                  <Text color="ui.secondaryText">
                    No metrics were saved for this creator yet.
                  </Text>
                )}
              </ContentSection>

              <ContentSection
                title={`Posts (${postItems.length})`}
                description={
                  postItems.length > 0
                    ? `Saved posts from ${postsDocuments.length} update${postsDocuments.length === 1 ? "" : "s"}, latest on ${formatDate(
                        latestPostsUpdatedAt,
                      )}.`
                    : undefined
                }
              >
                {postItems.length > 0 ? (
                  <Box overflowX="auto">
                    <Table.Root size={{ base: "sm", md: "md" }} minW="920px">
                      <Table.Header>
                        <Table.Row>
                          <Table.ColumnHeader>Post</Table.ColumnHeader>
                          <Table.ColumnHeader>Likes</Table.ColumnHeader>
                          <Table.ColumnHeader>Comments</Table.ColumnHeader>
                          <Table.ColumnHeader>Engagement</Table.ColumnHeader>
                          <Table.ColumnHeader>
                            ER (followers)
                          </Table.ColumnHeader>
                          <Table.ColumnHeader>Colabs</Table.ColumnHeader>
                          <Table.ColumnHeader>Usertags</Table.ColumnHeader>
                          <Table.ColumnHeader>Type</Table.ColumnHeader>
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
                                        `Instagram post ${index + 1}`}
                                    </Text>
                                    <Text
                                      mt={1}
                                      color="ui.secondaryText"
                                      fontSize="xs"
                                    >
                                      Updated {formatDate(updatedAt)} • Code{" "}
                                      {item.code}
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
                                        Paid partnership
                                      </Badge>
                                    ) : null}
                                  </Box>
                                </Flex>
                              </Table.Cell>
                              <Table.Cell>
                                {formatNumber(item.like_count ?? 0)}
                              </Table.Cell>
                              <Table.Cell>
                                {formatNumber(item.comment_count ?? 0)}
                              </Table.Cell>
                              <Table.Cell>
                                {formatNumber(engagement)}
                              </Table.Cell>
                              <Table.Cell>{formatPercent(postEr)}</Table.Cell>
                              <Table.Cell>
                                <Text fontWeight="bold">
                                  {formatNumber(
                                    item.coauthor_producers?.length ?? 0,
                                  )}
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
                                  {formatNumber(item.usertags?.length ?? 0)}
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
                                )}
                              </Table.Cell>
                            </Table.Row>
                          )
                        })}
                      </Table.Body>
                    </Table.Root>
                  </Box>
                ) : (
                  <Text color="ui.secondaryText">
                    No saved posts were returned for this creator.
                  </Text>
                )}
              </ContentSection>

              <ContentSection
                title={`Reels (${reelItems.length})`}
                description={
                  reelItems.length > 0
                    ? `Saved reels from ${reelsDocuments.length} update${reelsDocuments.length === 1 ? "" : "s"}, latest on ${formatDate(
                        latestReelsUpdatedAt,
                      )}.`
                    : undefined
                }
              >
                {reelItems.length > 0 ? (
                  <Box overflowX="auto">
                    <Table.Root size={{ base: "sm", md: "md" }} minW="860px">
                      <Table.Header>
                        <Table.Row>
                          <Table.ColumnHeader>Reel</Table.ColumnHeader>
                          <Table.ColumnHeader>Plays</Table.ColumnHeader>
                          <Table.ColumnHeader>Likes</Table.ColumnHeader>
                          <Table.ColumnHeader>Comments</Table.ColumnHeader>
                          <Table.ColumnHeader>Engagement</Table.ColumnHeader>
                          <Table.ColumnHeader>ER (plays)</Table.ColumnHeader>
                          <Table.ColumnHeader>Type</Table.ColumnHeader>
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
                                      Instagram reel {index + 1}
                                    </Text>
                                    <Text
                                      mt={1}
                                      color="ui.secondaryText"
                                      fontSize="xs"
                                    >
                                      Updated {formatDate(updatedAt)} • Code{" "}
                                      {item.code}
                                    </Text>
                                  </Box>
                                </Flex>
                              </Table.Cell>
                              <Table.Cell>
                                {formatNumber(item.play_count ?? 0)}
                              </Table.Cell>
                              <Table.Cell>
                                {formatNumber(item.like_count ?? 0)}
                              </Table.Cell>
                              <Table.Cell>
                                {formatNumber(item.comment_count ?? 0)}
                              </Table.Cell>
                              <Table.Cell>
                                {formatNumber(engagement)}
                              </Table.Cell>
                              <Table.Cell>{formatPercent(reelEr)}</Table.Cell>
                              <Table.Cell>
                                {getReelTypeLabel(
                                  item.media_type,
                                  item.product_type,
                                )}
                              </Table.Cell>
                            </Table.Row>
                          )
                        })}
                      </Table.Body>
                    </Table.Root>
                  </Box>
                ) : (
                  <Text color="ui.secondaryText">
                    No saved reels were returned for this creator.
                  </Text>
                )}
              </ContentSection>
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
            Close
          </Button>
        </DialogFooter>
      </DialogContent>
    </DialogRoot>
  )
}

export default CreatorSnapshotDetailDialog
