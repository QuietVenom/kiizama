import {
  Badge,
  Box,
  Flex,
  Grid,
  Heading,
  Icon,
  IconButton,
  Portal,
  SimpleGrid,
  Text,
  Tooltip,
} from "@chakra-ui/react"
import { useMutation } from "@tanstack/react-query"
import { createFileRoute } from "@tanstack/react-router"
import { useMemo, useState } from "react"
import {
  FiAlertCircle,
  FiClock,
  FiInfo,
  FiSearch,
  FiShield,
  FiTarget,
  FiUsers,
} from "react-icons/fi"

import {
  ApiError,
  IgProfileSnapshotsService,
  OpenAPI,
  type ProfileSnapshotExpanded,
  type ProfileSnapshotExpandedCollection,
} from "@/client"
import CreatorSnapshotCard from "@/components/CreatorsSearch/CreatorSnapshotCard"
import CreatorSnapshotDetailDialog from "@/components/CreatorsSearch/CreatorSnapshotDetailDialog"
import UsernameTagsInput from "@/components/CreatorsSearch/UsernameTagsInput"
import DashboardTopbar from "@/components/Dashboard/DashboardTopbar"
import { Button } from "@/components/ui/button"
import {
  DialogBody,
  DialogContent,
  DialogFooter,
  DialogHeader,
  DialogRoot,
  DialogTitle,
} from "@/components/ui/dialog"
import { Field } from "@/components/ui/field"
import {
  Skeleton,
  SkeletonCircle,
  SkeletonText,
} from "@/components/ui/skeleton"

export const Route = createFileRoute("/_layout/creators-search")({
  component: CreatorsSearchPage,
})

const MAX_USERNAMES = 50
const USERNAME_PATTERN = /^(?!.*\.\.)(?!\.)(?!.*\.$)[a-z0-9._]{1,30}$/

type OverviewCardTone = "brand" | "success" | "warning" | "danger"

const overviewToneStyles: Record<
  OverviewCardTone,
  { bg: string; color: string; labelColor: string }
> = {
  brand: {
    bg: "ui.brandSoft",
    color: "ui.brandText",
    labelColor: "ui.secondaryText",
  },
  success: {
    bg: "ui.successSoft",
    color: "ui.successText",
    labelColor: "ui.secondaryText",
  },
  warning: {
    bg: "ui.warningSoft",
    color: "ui.warningText",
    labelColor: "ui.secondaryText",
  },
  danger: {
    bg: "ui.dangerSoft",
    color: "ui.dangerText",
    labelColor: "ui.secondaryText",
  },
}

const normalizeUsername = (value: string) =>
  value.trim().replace(/^@+/, "").toLowerCase()

const sanitizeUsernames = (value: string[]) =>
  Array.from(
    new Set(value.map((item) => normalizeUsername(item)).filter(Boolean)),
  )

const isValidUsername = (value: string) => USERNAME_PATTERN.test(value)

const arraysEqual = (left: string[], right: string[]) =>
  left.length === right.length &&
  left.every((value, index) => value === right[index])

const REPORT_ENDPOINT_PATH = "/api/v1/social-media-report/instagram"

const extractFilename = (
  contentDisposition: string | null,
  username: string,
) => {
  if (contentDisposition) {
    const utf8Match = contentDisposition.match(/filename\*=UTF-8''([^;]+)/i)
    if (utf8Match?.[1]) {
      return decodeURIComponent(utf8Match[1])
    }

    const basicMatch = contentDisposition.match(/filename="?([^"]+)"?/i)
    if (basicMatch?.[1]) {
      return basicMatch[1]
    }
  }

  return `${username}_report.pdf`
}

const downloadBlob = (blob: Blob, filename: string) => {
  const objectUrl = window.URL.createObjectURL(blob)
  const link = document.createElement("a")

  link.href = objectUrl
  link.download = filename
  document.body.appendChild(link)
  link.click()
  document.body.removeChild(link)
  window.URL.revokeObjectURL(objectUrl)
}

const generateInstagramReportPdf = async (username: string) => {
  const token = localStorage.getItem("access_token") || ""
  const response = await fetch(`${OpenAPI.BASE}${REPORT_ENDPOINT_PATH}`, {
    method: "POST",
    headers: {
      Authorization: `Bearer ${token}`,
      "Content-Type": "application/json",
      Accept: "application/pdf",
    },
    body: JSON.stringify({
      usernames: [username],
      generate_html: false,
      generate_pdf: true,
    }),
  })

  if ([401, 403].includes(response.status)) {
    localStorage.removeItem("access_token")
    window.location.href = "/login"
    throw new Error("Your session has expired. Please log in again.")
  }

  if (!response.ok) {
    try {
      const errorBody = (await response.json()) as {
        detail?: Array<{ msg?: string }> | string
      }

      if (Array.isArray(errorBody.detail) && errorBody.detail[0]?.msg) {
        throw new Error(errorBody.detail[0].msg)
      }

      if (typeof errorBody.detail === "string") {
        throw new Error(errorBody.detail)
      }
    } catch (error) {
      if (error instanceof Error) {
        throw error
      }
    }

    throw new Error("Unable to generate the report.")
  }

  const blob = await response.blob()
  const filename = extractFilename(
    response.headers.get("Content-Disposition"),
    username,
  )

  downloadBlob(blob, filename)
}

const sortSnapshotsByUsernames = (
  snapshots: ProfileSnapshotExpanded[],
  usernames: string[],
) => {
  const usernameOrder = new Map(
    usernames.map((username, index) => [username, index] as const),
  )

  return [...snapshots].sort((left, right) => {
    const leftOrder =
      usernameOrder.get(left.profile?.username ?? "") ?? Number.MAX_SAFE_INTEGER
    const rightOrder =
      usernameOrder.get(right.profile?.username ?? "") ??
      Number.MAX_SAFE_INTEGER

    return leftOrder - rightOrder
  })
}

const extractApiErrorMessage = (error: unknown) => {
  if (error instanceof ApiError) {
    const detail = (error.body as { detail?: Array<{ msg?: string }> | string })
      ?.detail

    if (Array.isArray(detail) && detail.length > 0) {
      return detail[0]?.msg || "Unable to complete the search."
    }

    if (typeof detail === "string") {
      return detail
    }

    return error.message || "Unable to complete the search."
  }

  if (error instanceof Error) {
    return error.message
  }

  return "Unable to complete the search."
}

const getValidationMessage = (
  invalidUsernames: string[],
  overflowAttempted: boolean,
) => {
  if (invalidUsernames.length > 0) {
    return `Invalid usernames: ${invalidUsernames
      .map((username) => `@${username}`)
      .join(
        ", ",
      )}. Use lowercase letters, numbers, periods or underscores, up to 30 characters.`
  }

  if (overflowAttempted) {
    return "You can search up to 50 usernames per request."
  }

  return undefined
}

const GuideItem = ({
  description,
  icon,
  title,
}: {
  description: string
  icon: typeof FiSearch
  title: string
}) => (
  <Flex
    alignItems="flex-start"
    gap={3}
    rounded="2xl"
    borderWidth="1px"
    borderColor="ui.border"
    bg="ui.surfaceSoft"
    px={4}
    py={4}
  >
    <Flex
      boxSize="10"
      flexShrink={0}
      alignItems="center"
      justifyContent="center"
      rounded="2xl"
      bg="ui.brandSoft"
      color="ui.brandText"
    >
      <Icon as={icon} boxSize={5} />
    </Flex>
    <Box>
      <Text fontWeight="bold">{title}</Text>
      <Text mt={1} color="ui.secondaryText" fontSize="sm">
        {description}
      </Text>
    </Box>
  </Flex>
)

const SearchGuideDialog = ({
  onOpenChange,
  open,
}: {
  onOpenChange: (open: boolean) => void
  open: boolean
}) => (
  <DialogRoot
    open={open}
    placement="center"
    onOpenChange={({ open }) => onOpenChange(open)}
  >
    <DialogContent
      maxW={{ base: "calc(100vw - 1rem)", md: "680px" }}
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
        px={{ base: 6, md: 7 }}
        py={{ base: 6, md: 7 }}
      >
        <DialogTitle
          display="inline-flex"
          alignItems="center"
          minH="10"
          fontSize={{ base: "xl", md: "2xl" }}
          fontWeight="black"
          letterSpacing="-0.02em"
          lineHeight="1"
          whiteSpace="nowrap"
        >
          Search guide
        </DialogTitle>
        <Text mt={2} color="ui.secondaryText">
          Quick guidance for how creator search works and how results are
          presented.
        </Text>
      </DialogHeader>

      <DialogBody px={{ base: 5, md: 6 }} py={{ base: 5, md: 6 }}>
        <Flex direction="column" gap={3}>
          <GuideItem
            icon={FiSearch}
            title="Multi-creator search"
            description="Search the saved creator records for the usernames you enter, up to 50 at a time."
          />
          <GuideItem
            icon={FiClock}
            title="Saved profile details"
            description="Each result card opens a detailed view with profile information, metrics, posts, and reels when they are available."
          />
          <GuideItem
            icon={FiShield}
            title="Immediate issue highlighting"
            description="Invalid usernames and names that are not found are highlighted directly in the tags input and listed in a dedicated block below."
          />
        </Flex>
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

const SearchOverviewCard = ({
  label,
  tone,
  value,
}: {
  label: string
  tone: OverviewCardTone
  value: string
}) => {
  const toneStyle = overviewToneStyles[tone]

  return (
    <Box layerStyle="dashboardCard" px={5} py={5}>
      <Flex
        boxSize="11"
        alignItems="center"
        justifyContent="center"
        rounded="2xl"
        bg={toneStyle.bg}
        color={toneStyle.color}
      >
        <Icon
          as={
            tone === "danger"
              ? FiAlertCircle
              : tone === "warning"
                ? FiClock
                : tone === "success"
                  ? FiUsers
                  : FiTarget
          }
          boxSize={5}
        />
      </Flex>
      <Text mt={4} color={toneStyle.labelColor} fontSize="sm" fontWeight="bold">
        {label}
      </Text>
      <Text mt={1} fontSize={{ base: "2xl", lg: "3xl" }} fontWeight="black">
        {value}
      </Text>
    </Box>
  )
}

const ResultSkeletonCard = () => (
  <Box layerStyle="dashboardCard" p={{ base: 5, lg: 6 }}>
    <Flex gap={4}>
      <SkeletonCircle size="16" />
      <Box flex="1">
        <Skeleton height="5" maxW="220px" />
        <Skeleton height="4" mt={3} maxW="140px" />
        <SkeletonText mt={4} noOfLines={3} />
      </Box>
    </Flex>
    <Grid mt={6} templateColumns="repeat(3, minmax(0, 1fr))" gap={3}>
      <Skeleton height="16" rounded="2xl" />
      <Skeleton height="16" rounded="2xl" />
      <Skeleton height="16" rounded="2xl" />
    </Grid>
  </Box>
)

function CreatorsSearchPage() {
  const [isGuideOpen, setIsGuideOpen] = useState(false)
  const [usernames, setUsernames] = useState<string[]>([])
  const [submittedUsernames, setSubmittedUsernames] = useState<string[]>([])
  const [overflowAttempted, setOverflowAttempted] = useState(false)
  const [reportError, setReportError] = useState<string | null>(null)
  const [searchError, setSearchError] = useState<string | null>(null)
  const [searchResult, setSearchResult] =
    useState<ProfileSnapshotExpandedCollection | null>(null)
  const [selectedSnapshot, setSelectedSnapshot] =
    useState<ProfileSnapshotExpanded | null>(null)

  const invalidUsernames = useMemo(
    () => usernames.filter((username) => !isValidUsername(username)),
    [usernames],
  )
  const invalidSet = useMemo(
    () => new Set(invalidUsernames),
    [invalidUsernames],
  )
  const isSearchStale = useMemo(
    () =>
      submittedUsernames.length > 0 &&
      !arraysEqual(usernames, submittedUsernames),
    [submittedUsernames, usernames],
  )
  const missingUsernames = useMemo(
    () => (isSearchStale ? [] : (searchResult?.missing_usernames ?? [])),
    [isSearchStale, searchResult],
  )
  const expiredUsernames = useMemo(
    () => (isSearchStale ? [] : (searchResult?.expired_usernames ?? [])),
    [isSearchStale, searchResult],
  )
  const missingSet = useMemo(
    () => new Set(missingUsernames),
    [missingUsernames],
  )
  const expiredSet = useMemo(
    () => new Set(expiredUsernames),
    [expiredUsernames],
  )
  const sortedSnapshots = useMemo(
    () =>
      sortSnapshotsByUsernames(
        searchResult?.snapshots ?? [],
        submittedUsernames,
      ),
    [searchResult?.snapshots, submittedUsernames],
  )

  const validationMessage = getValidationMessage(
    invalidUsernames,
    overflowAttempted,
  )
  const hasValidationIssue = Boolean(validationMessage)
  const hasSearched =
    submittedUsernames.length > 0 ||
    searchResult !== null ||
    searchError !== null

  const searchMutation = useMutation({
    mutationFn: (requestedUsernames: string[]) =>
      IgProfileSnapshotsService.readIgProfileSnapshotsAdvanced({
        limit: MAX_USERNAMES,
        usernames: requestedUsernames,
      }),
    onMutate: (requestedUsernames) => {
      setReportError(null)
      setSubmittedUsernames(requestedUsernames)
      setSearchError(null)
      setSearchResult(null)
      setSelectedSnapshot(null)
    },
    onSuccess: (data) => {
      setSearchResult(data)
    },
    onError: (error) => {
      setSearchError(extractApiErrorMessage(error))
    },
  })

  const reportMutation = useMutation({
    mutationFn: generateInstagramReportPdf,
    onMutate: () => {
      setReportError(null)
    },
    onError: (error) => {
      setReportError(extractApiErrorMessage(error))
    },
  })

  const handleUsernamesChange = (nextValue: string[]) => {
    const sanitizedValue = sanitizeUsernames(nextValue)
    setUsernames(sanitizedValue)

    if (sanitizedValue.length < MAX_USERNAMES) {
      setOverflowAttempted(false)
    }
  }

  const handleSearch = () => {
    const nextUsernames = sanitizeUsernames(usernames)
    const nextInvalidUsernames = nextUsernames.filter(
      (username) => !isValidUsername(username),
    )

    setUsernames(nextUsernames)
    setOverflowAttempted(false)

    if (nextUsernames.length === 0 || nextInvalidUsernames.length > 0) {
      return
    }

    searchMutation.mutate(nextUsernames)
  }

  return (
    <Box minH="100vh" bg="ui.page">
      <DashboardTopbar />

      <Box px={{ base: 4, md: 7, lg: 10 }} py={{ base: 7, lg: 9 }}>
        <Flex
          mb={{ base: 7, lg: 8 }}
          alignItems={{ base: "flex-start", lg: "flex-start" }}
          justifyContent="space-between"
          gap={{ base: 4, lg: 6 }}
          direction={{ base: "column", lg: "row" }}
        >
          <Box flex="1" minW={0}>
            <Text textStyle="eyebrow">Creators Search</Text>
            <Heading
              mt={3}
              textStyle="pageTitle"
              fontSize={{ base: "3xl", lg: "4xl" }}
              fontWeight="black"
              lineHeight="1.05"
              maxW="24ch"
            >
              Search saved creator profiles in one request.
            </Heading>
            <Text
              mt={3}
              color="ui.secondaryText"
              fontSize={{ base: "md", lg: "lg" }}
              maxW="68ch"
            >
              Add multiple Instagram usernames, review which creators are
              already stored in the platform, and open a complete view for each
              match.
            </Text>
          </Box>

          <Button
            variant="outline"
            alignSelf={{ base: "stretch", lg: "flex-start" }}
            onClick={() => setIsGuideOpen(true)}
          >
            <FiInfo />
            Search guide
          </Button>
        </Flex>

        <Box
          layerStyle="dashboardCard"
          p={{ base: 5, md: 6, lg: 7 }}
          mb={{ base: 7, lg: 8 }}
        >
          <Box>
            <Text
              fontSize="sm"
              color="ui.mutedText"
              fontWeight="bold"
              letterSpacing="0.08em"
            >
              MULTI-USERNAME LOOKUP
            </Text>
            <Flex mt={2} alignItems="center" gap={2}>
              <Heading size="lg">Search creators by username</Heading>
              <Tooltip.Root openDelay={160} positioning={{ placement: "top" }}>
                <Tooltip.Trigger asChild>
                  <IconButton
                    aria-label="Search help"
                    variant="ghost"
                    size="sm"
                    color="ui.mutedText"
                    _hover={{ bg: "ui.surfaceSoft", color: "ui.text" }}
                  >
                    <FiInfo />
                  </IconButton>
                </Tooltip.Trigger>
                <Portal>
                  <Tooltip.Positioner>
                    <Tooltip.Content
                      maxW="320px"
                      rounded="2xl"
                      borderWidth="1px"
                      borderColor="ui.border"
                      bg="ui.panel"
                      px={4}
                      py={3}
                      color="ui.text"
                      boxShadow="lg"
                    >
                      <Tooltip.Arrow>
                        <Tooltip.ArrowTip />
                      </Tooltip.Arrow>
                      <Text fontSize="sm" lineHeight="1.7">
                        Paste a list, press Enter, or separate usernames with
                        commas. Usernames are normalized to lowercase and any
                        leading @ is removed automatically before the search
                        runs.
                      </Text>
                    </Tooltip.Content>
                  </Tooltip.Positioner>
                </Portal>
              </Tooltip.Root>
            </Flex>
          </Box>

          <Field
            mt={5}
            label="Instagram usernames"
            helperText={
              hasValidationIssue ? undefined : "Up to 50 usernames per request."
            }
            errorText={validationMessage}
            invalid={hasValidationIssue}
          >
            <UsernameTagsInput
              expiredValues={expiredSet}
              invalid={hasValidationIssue}
              invalidValues={invalidSet}
              missingValues={missingSet}
              onMaxExceeded={() => setOverflowAttempted(true)}
              onValueChange={handleUsernamesChange}
              placeholder="creator_one, brand.partner, another_creator"
              value={usernames}
            />
          </Field>

          <Flex
            mt={4}
            alignItems="center"
            justifyContent="space-between"
            gap={3}
            wrap="wrap"
          >
            <Flex alignItems="center" gap={2} wrap="wrap">
              <Badge
                rounded="full"
                borderWidth="1px"
                borderColor="ui.borderSoft"
                bg="ui.surfaceSoft"
                color="ui.secondaryText"
                px={3}
                py={1.5}
              >
                {usernames.length} / {MAX_USERNAMES} usernames
              </Badge>
              {isSearchStale ? (
                <Badge
                  rounded="full"
                  bg="ui.infoSoft"
                  color="ui.infoText"
                  px={3}
                  py={1.5}
                >
                  Input changed, search again to refresh
                </Badge>
              ) : null}
            </Flex>

            <Button
              layerStyle="brandGradientButton"
              loading={searchMutation.isPending}
              onClick={handleSearch}
              disabled={
                usernames.length === 0 ||
                invalidUsernames.length > 0 ||
                searchMutation.isPending
              }
            >
              <FiSearch />
              Search creators
            </Button>
          </Flex>
        </Box>

        {searchError ? (
          <Box
            mb={{ base: 6, lg: 7 }}
            rounded="3xl"
            borderWidth="1px"
            borderColor="ui.danger"
            bg="ui.dangerSoft"
            px={{ base: 5, md: 6 }}
            py={{ base: 4, md: 5 }}
          >
            <Flex alignItems="flex-start" gap={3}>
              <Flex
                boxSize="10"
                flexShrink={0}
                alignItems="center"
                justifyContent="center"
                rounded="2xl"
                bg="rgba(220, 38, 38, 0.10)"
                color="ui.dangerText"
              >
                <Icon as={FiAlertCircle} boxSize={5} />
              </Flex>
              <Box>
                <Text color="ui.dangerText" fontWeight="black">
                  Search failed
                </Text>
                <Text mt={1} color="ui.secondaryText">
                  {searchError}
                </Text>
              </Box>
            </Flex>
          </Box>
        ) : null}

        {reportError ? (
          <Box
            mb={{ base: 6, lg: 7 }}
            rounded="3xl"
            borderWidth="1px"
            borderColor="ui.danger"
            bg="ui.dangerSoft"
            px={{ base: 5, md: 6 }}
            py={{ base: 4, md: 5 }}
          >
            <Flex alignItems="flex-start" gap={3}>
              <Flex
                boxSize="10"
                flexShrink={0}
                alignItems="center"
                justifyContent="center"
                rounded="2xl"
                bg="rgba(220, 38, 38, 0.10)"
                color="ui.dangerText"
              >
                <Icon as={FiAlertCircle} boxSize={5} />
              </Flex>
              <Box>
                <Text color="ui.dangerText" fontWeight="black">
                  Report generation failed
                </Text>
                <Text mt={1} color="ui.secondaryText">
                  {reportError}
                </Text>
              </Box>
            </Flex>
          </Box>
        ) : null}

        {hasSearched && !searchMutation.isPending ? (
          <SimpleGrid
            columns={{ base: 1, md: 2, xl: 4 }}
            gap={5}
            mb={{ base: 6, lg: 7 }}
          >
            <SearchOverviewCard
              label="Requested usernames"
              tone="brand"
              value={String(submittedUsernames.length)}
            />
            <SearchOverviewCard
              label="Profiles found"
              tone="success"
              value={String(sortedSnapshots.length)}
            />
            <SearchOverviewCard
              label="Expired profiles"
              tone="warning"
              value={String(expiredUsernames.length)}
            />
            <SearchOverviewCard
              label="Usernames not found"
              tone="danger"
              value={String(missingUsernames.length)}
            />
          </SimpleGrid>
        ) : null}

        {expiredUsernames.length > 0 ? (
          <Box
            mb={{ base: 6, lg: 7 }}
            rounded="3xl"
            borderWidth="1px"
            borderColor="ui.warning"
            bg="ui.warningSoft"
            px={{ base: 5, md: 6 }}
            py={{ base: 5, md: 6 }}
          >
            <Text color="ui.warningText" fontSize="lg" fontWeight="black">
              Expired profiles detected
            </Text>
            <Text mt={2} color="ui.secondaryText" maxW="56ch">
              These creators exist in saved data, but their profile image URL
              has already expired. They are highlighted in yellow above and in
              the results list.
            </Text>

            <Flex mt={4} gap={2} wrap="wrap">
              {expiredUsernames.map((username) => (
                <Badge
                  key={username}
                  rounded="full"
                  borderWidth="1px"
                  borderColor="ui.warning"
                  bg="ui.panel"
                  color="ui.warningText"
                  px={3}
                  py={1.5}
                >
                  @{username}
                </Badge>
              ))}
            </Flex>
          </Box>
        ) : null}

        {missingUsernames.length > 0 ? (
          <Box
            mb={{ base: 6, lg: 7 }}
            rounded="3xl"
            borderWidth="1px"
            borderColor="ui.danger"
            bg="ui.dangerSoft"
            px={{ base: 5, md: 6 }}
            py={{ base: 5, md: 6 }}
          >
            <Text color="ui.dangerText" fontSize="lg" fontWeight="black">
              Usernames not found
            </Text>
            <Text mt={2} color="ui.secondaryText" maxW="56ch">
              These usernames were not found in the saved creator data. They are
              also highlighted in red above.
            </Text>

            <Flex mt={4} gap={2} wrap="wrap">
              {missingUsernames.map((username) => (
                <Badge
                  key={username}
                  rounded="full"
                  borderWidth="1px"
                  borderColor="ui.danger"
                  bg="ui.panel"
                  color="ui.dangerText"
                  px={3}
                  py={1.5}
                >
                  @{username}
                </Badge>
              ))}
            </Flex>
          </Box>
        ) : null}

        {searchMutation.isPending ? (
          <SimpleGrid columns={{ base: 1, xl: 2 }} gap={6}>
            <ResultSkeletonCard />
            <ResultSkeletonCard />
            <ResultSkeletonCard />
            <ResultSkeletonCard />
          </SimpleGrid>
        ) : sortedSnapshots.length > 0 ? (
          <SimpleGrid columns={{ base: 1, xl: 2 }} gap={6}>
            {sortedSnapshots.map((snapshot) => (
              <CreatorSnapshotCard
                key={
                  snapshot._id ||
                  `${snapshot.profile_id}-${snapshot.scraped_at}`
                }
                isGeneratingReport={
                  reportMutation.isPending &&
                  reportMutation.variables === snapshot.profile?.username
                }
                isExpired={expiredSet.has(snapshot.profile?.username ?? "")}
                onGenerateReport={
                  snapshot.profile?.username
                    ? () => reportMutation.mutate(snapshot.profile!.username)
                    : undefined
                }
                snapshot={snapshot}
                onOpenDetails={() => setSelectedSnapshot(snapshot)}
              />
            ))}
          </SimpleGrid>
        ) : hasSearched && !searchError ? (
          <Box layerStyle="dashboardCard" p={{ base: 6, md: 8 }}>
            <Text
              fontSize="sm"
              color="ui.mutedText"
              fontWeight="bold"
              letterSpacing="0.08em"
            >
              EMPTY RESULT
            </Text>
            <Heading mt={2} size="md">
              No creator snapshots matched this search.
            </Heading>
            <Text mt={3} color="ui.secondaryText" maxW="56ch">
              Try another set of usernames or verify that those creators are
              already available in the saved creator data.
            </Text>
          </Box>
        ) : (
          <Box layerStyle="dashboardCard" p={{ base: 6, md: 8 }}>
            <Text
              fontSize="sm"
              color="ui.mutedText"
              fontWeight="bold"
              letterSpacing="0.08em"
            >
              READY TO SEARCH
            </Text>
            <Heading mt={2} size="md">
              Add usernames to start exploring creator data.
            </Heading>
            <Text mt={3} color="ui.secondaryText" maxW="58ch">
              Once you launch a search, found creators will appear here as cards
              and each card will open a detail modal with profile metrics,
              recent posts, and reels.
            </Text>
          </Box>
        )}
      </Box>

      <CreatorSnapshotDetailDialog
        snapshot={selectedSnapshot}
        onOpenChange={(open) => {
          if (!open) {
            setSelectedSnapshot(null)
          }
        }}
      />
      <SearchGuideDialog open={isGuideOpen} onOpenChange={setIsGuideOpen} />
    </Box>
  )
}
