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
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import { createFileRoute } from "@tanstack/react-router"
import {
  type RefObject,
  useCallback,
  useEffect,
  useMemo,
  useRef,
  useState,
} from "react"
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
  type CreatorsSearchHistoryCreateRequest,
  type CreatorsSearchHistoryItem,
  CreatorsSearchHistoryService,
  IgProfileSnapshotsService,
  type InstagramBatchScrapeSummaryResponse,
  type InstagramScrapeJobStatusResponse,
  InstagramService,
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
import {
  createIdempotencyKey,
  invalidateBillingSummary,
} from "@/features/billing/api"
import { subscribeToUserEvents } from "@/features/user-events/connection"
import {
  isIgScrapeJobCompletedEvent,
  isIgScrapeJobFailedEvent,
  type UserEvent,
} from "@/features/user-events/types"
import { extractApiErrorMessage } from "@/lib/api-errors"
import {
  buildCreatorsSearchBatchKey,
  type CreatorsSearchJobSourceBox,
  type CreatorsSearchJobStatus,
  type CreatorsSearchLocalJob,
  createBalancedUsernameBatches,
  hasActiveCreatorsSearchJob,
  readCreatorsSearchJobs,
  removeCreatorsSearchJob,
  subscribeToCreatorsSearchJobs,
  updateCreatorsSearchJob,
  upsertCreatorsSearchJob,
} from "@/lib/creators-search-jobs"
import {
  areStringArraysEqual,
  isValidInstagramUsername,
  sanitizeInstagramUsernames,
} from "@/lib/instagram-usernames"
import {
  downloadBlob,
  extractFilenameFromContentDisposition,
} from "@/lib/report-files"

export const Route = createFileRoute("/_layout/creators-search")({
  component: CreatorsSearchPage,
})

const MAX_USERNAMES = 50

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

const REPORT_ENDPOINT_PATH = "/api/v1/social-media-report/instagram"
const SEARCH_HISTORY_PREVIEW_LIMIT = 5
const SEARCH_HISTORY_VIEW_ALL_LIMIT = 20
const creatorsSearchHistoryQueryKey = (limit: number) =>
  ["creators-search-history", limit] as const
const jobTimestampFormatter = new Intl.DateTimeFormat("en-US", {
  day: "2-digit",
  hour: "2-digit",
  minute: "2-digit",
  month: "short",
})

const getReadyUsernamesFromSummary = (
  summary?: InstagramBatchScrapeSummaryResponse | null,
) =>
  (summary?.usernames ?? [])
    .filter((item) => item.status === "success" || item.status === "skipped")
    .map((item) => item.username)

const getReadyUsernamesFromSearchResult = (
  requestedUsernames: string[],
  result: ProfileSnapshotExpandedCollection,
) => {
  const expiredUsernames = new Set(result.expired_usernames ?? [])
  const foundUsernames = new Set(
    (result.snapshots ?? [])
      .map((snapshot) => snapshot.profile?.username ?? "")
      .filter(Boolean),
  )

  return requestedUsernames.filter(
    (username) =>
      foundUsernames.has(username) && !expiredUsernames.has(username),
  )
}

const buildTerminalPayloadFromJobStatus = (
  response: InstagramScrapeJobStatusResponse,
  fallbackRequestedUsernames: string[],
) => {
  if (response.status !== "done" && response.status !== "failed") {
    return null
  }

  const summaryUsernames = response.summary?.usernames ?? []
  const requestedUsernames =
    summaryUsernames.length > 0
      ? summaryUsernames.map((item) => item.username)
      : (response.references?.all_usernames ?? fallbackRequestedUsernames)
  const successfulUsernames =
    summaryUsernames.length > 0
      ? summaryUsernames
          .filter((item) => item.status === "success")
          .map((item) => item.username)
      : (response.references?.successful_usernames ?? [])
  const skippedUsernames =
    summaryUsernames.length > 0
      ? summaryUsernames
          .filter((item) => item.status === "skipped")
          .map((item) => item.username)
      : (response.references?.skipped_usernames ?? [])
  const failedUsernames =
    summaryUsernames.length > 0
      ? summaryUsernames
          .filter((item) => item.status === "failed")
          .map((item) => item.username)
      : (response.references?.failed_usernames ?? [])
  const notFoundUsernames =
    summaryUsernames.length > 0
      ? summaryUsernames
          .filter((item) => item.status === "not_found")
          .map((item) => item.username)
      : (response.references?.not_found_usernames ?? [])

  return {
    event_version: 1 as const,
    notification_id: `job:${response.job_id}:fallback`,
    job_id: response.job_id,
    status: response.status,
    created_at: response.created_at,
    completed_at: response.updated_at,
    requested_usernames: requestedUsernames,
    ready_usernames: [...successfulUsernames, ...skippedUsernames],
    successful_usernames: successfulUsernames,
    skipped_usernames: skippedUsernames,
    failed_usernames: failedUsernames,
    not_found_usernames: notFoundUsernames,
    counters: {
      requested:
        response.summary?.counters?.requested ?? requestedUsernames.length,
      successful:
        response.summary?.counters?.successful ?? successfulUsernames.length,
      failed: response.summary?.counters?.failed ?? failedUsernames.length,
      not_found:
        response.summary?.counters?.not_found ?? notFoundUsernames.length,
    },
    error: response.error ?? response.summary?.error ?? null,
  }
}

const syncLocalJobWithStatusResponse = (
  job: CreatorsSearchLocalJob,
  response: InstagramScrapeJobStatusResponse,
) => {
  const terminalPayload = buildTerminalPayloadFromJobStatus(
    response,
    job.requestedUsernames,
  )
  const nextStatus: CreatorsSearchJobStatus =
    response.status === "done" || response.status === "failed"
      ? response.status
      : "queued"

  return {
    ...job,
    status: nextStatus,
    updatedAt: response.updated_at,
    readyUsernames:
      terminalPayload?.ready_usernames ??
      getReadyUsernamesFromSummary(response.summary),
    error: response.error ?? response.summary?.error ?? null,
    terminalPayload: terminalPayload ?? job.terminalPayload,
  }
}

const formatJobTimestamp = (value: string) => {
  const parsedDate = new Date(value)
  if (Number.isNaN(parsedDate.getTime())) {
    return value
  }

  return jobTimestampFormatter.format(parsedDate)
}

const getJobStatusStyles = (status: CreatorsSearchJobStatus) => {
  if (status === "done") {
    return {
      bg: "ui.successSoft",
      borderColor: "ui.success",
      textColor: "ui.successText",
    }
  }

  if (status === "failed") {
    return {
      bg: "ui.dangerSoft",
      borderColor: "ui.danger",
      textColor: "ui.dangerText",
    }
  }

  return {
    bg: "ui.infoSoft",
    borderColor: "ui.infoText",
    textColor: "ui.infoText",
  }
}

const getJobStatusLabel = (status: CreatorsSearchJobStatus) => {
  if (status === "done") {
    return "Done"
  }

  if (status === "failed") {
    return "Failed"
  }

  return "Queued"
}

const scrollPageTopIntoView = (targetRef: RefObject<HTMLElement | null>) => {
  targetRef.current?.scrollIntoView({ behavior: "smooth", block: "start" })
}

const JobUsernamesSection = ({
  title,
  tone,
  usernames,
}: {
  title: string
  tone: "success" | "danger" | "warning" | "neutral"
  usernames: string[]
}) => {
  const toneStyles =
    tone === "success"
      ? {
          borderColor: "ui.success",
          bg: "ui.successSoft",
          textColor: "ui.successText",
        }
      : tone === "danger"
        ? {
            borderColor: "ui.danger",
            bg: "ui.dangerSoft",
            textColor: "ui.dangerText",
          }
        : tone === "warning"
          ? {
              borderColor: "ui.warning",
              bg: "ui.warningSoft",
              textColor: "ui.warningText",
            }
          : {
              borderColor: "ui.border",
              bg: "ui.surfaceSoft",
              textColor: "ui.text",
            }

  return (
    <Box
      rounded="2xl"
      borderWidth="1px"
      borderColor={toneStyles.borderColor}
      bg={toneStyles.bg}
      px={4}
      py={4}
    >
      <Flex alignItems="center" justifyContent="space-between" gap={3}>
        <Text color={toneStyles.textColor} fontWeight="black">
          {title}
        </Text>
        <Badge
          rounded="full"
          borderWidth="1px"
          borderColor="ui.borderSoft"
          bg="ui.panel"
          color={toneStyles.textColor}
          px={3}
          py={1.5}
        >
          {usernames.length}
        </Badge>
      </Flex>

      {usernames.length === 0 ? (
        <Text mt={3} color="ui.secondaryText" fontSize="sm">
          No usernames in this group.
        </Text>
      ) : (
        <Flex mt={3} gap={2} wrap="wrap">
          {usernames.map((username) => (
            <Badge
              key={`${title}-${username}`}
              rounded="full"
              borderWidth="1px"
              borderColor="ui.borderSoft"
              bg="ui.panel"
              color="ui.text"
              px={3}
              py={1.5}
            >
              @{username}
            </Badge>
          ))}
        </Flex>
      )}
    </Box>
  )
}

const SearchHistoryCard = ({
  compact = false,
  item,
  onClick,
}: {
  compact?: boolean
  item: CreatorsSearchHistoryItem
  onClick: (usernames: string[]) => void
}) => {
  const readyUsernames = item.ready_usernames ?? []
  const visibleUsernames = readyUsernames.slice(0, 5)
  const hiddenUsernamesCount = Math.max(
    readyUsernames.length - visibleUsernames.length,
    0,
  )

  if (compact) {
    return (
      <Box
        as="button"
        rounded="2xl"
        borderWidth="1px"
        borderColor="ui.border"
        bg="ui.surfaceSoft"
        p={4}
        minH="0"
        aspectRatio={1}
        display="flex"
        flexDirection="column"
        textAlign="left"
        transition="transform 180ms ease, box-shadow 180ms ease, border-color 180ms ease"
        cursor="pointer"
        _hover={{
          boxShadow: "md",
          borderColor: "ui.brandText",
        }}
        onClick={() => onClick(readyUsernames)}
      >
        <Flex alignItems="flex-start" justifyContent="space-between" gap={3}>
          <Text color="ui.text" fontWeight="black" lineClamp={2} minW={0}>
            {item.source === "ig-scrape-job" && item.job_id
              ? item.job_id
              : "Direct search"}
          </Text>
          <Badge
            rounded="full"
            borderWidth="1px"
            borderColor="ui.borderSoft"
            bg="ui.panel"
            color="ui.brandText"
            px={3}
            py={1.5}
            flexShrink={0}
          >
            {readyUsernames.length}
          </Badge>
        </Flex>

        <Text mt={3} color="ui.secondaryText" fontSize="sm">
          {formatJobTimestamp(item.created_at)}
        </Text>

        <Flex mt={4} gap={2} wrap="wrap" alignContent="flex-start">
          {visibleUsernames.map((username) => (
            <Badge
              key={`${item.id}-${username}`}
              rounded="full"
              borderWidth="1px"
              borderColor="ui.borderSoft"
              bg="ui.panel"
              color="ui.text"
              px={3}
              py={1.5}
            >
              @{username}
            </Badge>
          ))}
          {hiddenUsernamesCount > 0 ? (
            <Badge
              rounded="full"
              borderWidth="1px"
              borderColor="ui.borderSoft"
              bg="ui.panel"
              color="ui.secondaryText"
              px={3}
              py={1.5}
            >
              +{hiddenUsernamesCount}
            </Badge>
          ) : null}
        </Flex>
      </Box>
    )
  }

  return (
    <Box
      as="button"
      rounded="2xl"
      borderWidth="1px"
      borderColor="ui.border"
      bg="ui.surfaceSoft"
      px={4}
      py={4}
      textAlign="left"
      transition="transform 180ms ease, box-shadow 180ms ease, border-color 180ms ease"
      cursor="pointer"
      _hover={{
        transform: "translateY(-1px)",
        boxShadow: "md",
        borderColor: "ui.brandText",
      }}
      onClick={() => onClick(readyUsernames)}
    >
      <Flex alignItems="flex-start" justifyContent="space-between" gap={3}>
        <Box minW={0}>
          <Text color="ui.text" fontWeight="black">
            {item.source === "ig-scrape-job" && item.job_id
              ? item.job_id
              : "Direct search"}
          </Text>
          <Text mt={1} color="ui.secondaryText" fontSize="sm">
            {item.source === "ig-scrape-job"
              ? "Ready usernames from scrape job"
              : "Ready usernames from direct search"}
          </Text>
        </Box>
        <Badge
          rounded="full"
          borderWidth="1px"
          borderColor="ui.borderSoft"
          bg="ui.panel"
          color="ui.brandText"
          px={3}
          py={1.5}
        >
          {readyUsernames.length}
        </Badge>
      </Flex>

      <Text mt={3} color="ui.secondaryText" fontSize="sm">
        {formatJobTimestamp(item.created_at)}
      </Text>

      <Flex mt={3} gap={2} wrap="wrap">
        {readyUsernames.map((username) => (
          <Badge
            key={`${item.id}-${username}`}
            rounded="full"
            borderWidth="1px"
            borderColor="ui.borderSoft"
            bg="ui.panel"
            color="ui.text"
            px={3}
            py={1.5}
          >
            @{username}
          </Badge>
        ))}
      </Flex>
    </Box>
  )
}

const SearchHistoryViewAllDialog = ({
  items,
  loading,
  onOpenChange,
  onReuseReadyUsernames,
  open,
}: {
  items: CreatorsSearchHistoryItem[]
  loading: boolean
  onOpenChange: (open: boolean) => void
  onReuseReadyUsernames: (usernames: string[]) => void
  open: boolean
}) => (
  <DialogRoot
    open={open}
    placement="center"
    onOpenChange={({ open: nextOpen }) => onOpenChange(nextOpen)}
  >
    <DialogContent
      maxW={{ base: "calc(100vw - 1rem)", md: "860px" }}
      maxH={{ base: "calc(100vh - 1rem)", md: "calc(100vh - 4rem)" }}
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
          Search history
        </DialogTitle>
        <Text mt={2} color="ui.secondaryText">
          Reuse any of the last 20 successful ready username lists.
        </Text>
      </DialogHeader>

      <DialogBody
        px={{ base: 5, md: 6 }}
        py={{ base: 5, md: 6 }}
        overflowY="auto"
      >
        {loading ? (
          <Flex direction="column" gap={3}>
            <ResultSkeletonCard />
            <ResultSkeletonCard />
          </Flex>
        ) : items.length === 0 ? (
          <Box
            rounded="2xl"
            borderWidth="1px"
            borderColor="ui.border"
            bg="ui.surfaceSoft"
            px={4}
            py={4}
          >
            <Text color="ui.secondaryText" fontSize="sm" fontWeight="bold">
              No search history available yet.
            </Text>
          </Box>
        ) : (
          <Flex direction="column" gap={3}>
            {items.map((item) => (
              <SearchHistoryCard
                key={item.id}
                item={item}
                onClick={(usernames) => onReuseReadyUsernames(usernames)}
              />
            ))}
          </Flex>
        )}
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

const CurrentJobDetailDialog = ({
  job,
  onOpenChange,
  onReuseReadyUsernames,
}: {
  job: CreatorsSearchLocalJob | null
  onOpenChange: (open: boolean) => void
  onReuseReadyUsernames: (usernames: string[]) => void
}) => {
  const terminalPayload = job?.terminalPayload
  const requestedUsernames =
    terminalPayload?.requested_usernames ?? job?.requestedUsernames ?? []
  const readyUsernames =
    terminalPayload?.ready_usernames ?? job?.readyUsernames ?? []
  const failedUsernames = terminalPayload?.failed_usernames ?? []
  const notFoundUsernames = terminalPayload?.not_found_usernames ?? []
  const skippedUsernames = terminalPayload?.skipped_usernames ?? []
  const successfulUsernames = terminalPayload?.successful_usernames ?? []

  return (
    <DialogRoot
      open={job !== null}
      placement="center"
      onOpenChange={({ open }) => onOpenChange(open)}
    >
      <DialogContent
        maxW={{ base: "calc(100vw - 1rem)", md: "860px" }}
        maxH={{ base: "calc(100vh - 1rem)", md: "calc(100vh - 4rem)" }}
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
            display="flex"
            alignItems={{ base: "flex-start", md: "center" }}
            justifyContent="space-between"
            gap={3}
            flexDirection={{ base: "column", md: "row" }}
          >
            <Box minW={0}>
              <Text
                color="ui.mutedText"
                fontSize="sm"
                fontWeight="bold"
                letterSpacing="0.08em"
              >
                CURRENT JOB DETAIL
              </Text>
              <Text
                mt={2}
                fontSize={{ base: "lg", md: "xl" }}
                fontWeight="black"
                lineHeight="1.2"
                wordBreak="break-word"
              >
                {job?.jobId ?? "Job detail"}
              </Text>
            </Box>
            {job ? (
              <Badge
                rounded="full"
                borderWidth="1px"
                borderColor={getJobStatusStyles(job.status).borderColor}
                bg="ui.panel"
                color={getJobStatusStyles(job.status).textColor}
                px={3}
                py={1.5}
              >
                {getJobStatusLabel(job.status)}
              </Badge>
            ) : null}
          </DialogTitle>
          {job ? (
            <Text mt={2} color="ui.secondaryText">
              {job.sourceBox === "expired"
                ? "Profiles need updates"
                : "Usernames not found"}{" "}
              batch updated {formatJobTimestamp(job.updatedAt)}.
            </Text>
          ) : null}
        </DialogHeader>

        <DialogBody
          px={{ base: 5, md: 6 }}
          py={{ base: 5, md: 6 }}
          overflowY="auto"
        >
          {job ? (
            <Flex direction="column" gap={4}>
              <SimpleGrid columns={{ base: 1, sm: 2, xl: 4 }} gap={3}>
                <SearchOverviewCard
                  label="Requested"
                  tone="brand"
                  value={String(
                    terminalPayload?.counters.requested ??
                      requestedUsernames.length,
                  )}
                />
                <SearchOverviewCard
                  label="Ready"
                  tone="success"
                  value={String(readyUsernames.length)}
                />
                <SearchOverviewCard
                  label="Failed"
                  tone="danger"
                  value={String(
                    terminalPayload?.counters.failed ?? failedUsernames.length,
                  )}
                />
                <SearchOverviewCard
                  label="Not found"
                  tone="warning"
                  value={String(
                    terminalPayload?.counters.not_found ??
                      notFoundUsernames.length,
                  )}
                />
              </SimpleGrid>

              <JobUsernamesSection
                title="Requested usernames"
                tone="neutral"
                usernames={requestedUsernames}
              />
              <JobUsernamesSection
                title="Ready usernames"
                tone="success"
                usernames={readyUsernames}
              />
              <JobUsernamesSection
                title="Successful usernames"
                tone="success"
                usernames={successfulUsernames}
              />
              <JobUsernamesSection
                title="Skipped usernames"
                tone="warning"
                usernames={skippedUsernames}
              />
              <JobUsernamesSection
                title="Failed usernames"
                tone="danger"
                usernames={failedUsernames}
              />
              <JobUsernamesSection
                title="Not found usernames"
                tone="warning"
                usernames={notFoundUsernames}
              />

              {job.error ? (
                <Box
                  rounded="2xl"
                  borderWidth="1px"
                  borderColor="ui.danger"
                  bg="ui.dangerSoft"
                  px={4}
                  py={4}
                >
                  <Text color="ui.dangerText" fontWeight="black">
                    Worker error
                  </Text>
                  <Text mt={2} color="ui.secondaryText" fontSize="sm">
                    {job.error}
                  </Text>
                </Box>
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
          justifyContent="space-between"
          gap={3}
          flexDirection={{ base: "column-reverse", md: "row" }}
        >
          <Button variant="outline" onClick={() => onOpenChange(false)}>
            Close
          </Button>
          {job && readyUsernames.length > 0 ? (
            <Button
              layerStyle="brandGradientButton"
              onClick={() => onReuseReadyUsernames(readyUsernames)}
            >
              <FiSearch />
              Search
            </Button>
          ) : null}
        </DialogFooter>
      </DialogContent>
    </DialogRoot>
  )
}

const generateInstagramReportPdf = async (username: string) => {
  const token = localStorage.getItem("access_token") || ""
  const response = await fetch(`${OpenAPI.BASE}${REPORT_ENDPOINT_PATH}`, {
    method: "POST",
    headers: {
      Authorization: `Bearer ${token}`,
      "Content-Type": "application/json",
      Accept: "application/pdf",
      "Idempotency-Key": createIdempotencyKey(),
    },
    body: JSON.stringify({
      usernames: [username],
      generate_html: false,
      generate_pdf: true,
    }),
  })

  if (response.status === 401) {
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
  const filename = extractFilenameFromContentDisposition(
    response.headers.get("Content-Disposition"),
    `${username}_report.pdf`,
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
        alignItems="flex-start"
        justifyContent="space-between"
        gap={4}
        direction="column"
      >
        <Flex alignItems="center" gap={3} minW={0}>
          <Flex
            boxSize="11"
            flexShrink={0}
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
          <Text color={toneStyle.labelColor} fontSize="sm" fontWeight="bold">
            {label}
          </Text>
        </Flex>

        <Text
          w="full"
          textAlign="center"
          fontSize={{ base: "3xl", lg: "4xl" }}
          fontWeight="black"
          lineHeight="1"
        >
          {value}
        </Text>
      </Flex>
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
  const queryClient = useQueryClient()
  const [isGuideOpen, setIsGuideOpen] = useState(false)
  const [isSearchHistoryOpen, setIsSearchHistoryOpen] = useState(false)
  const [usernames, setUsernames] = useState<string[]>([])
  const [submittedUsernames, setSubmittedUsernames] = useState<string[]>([])
  const [overflowAttempted, setOverflowAttempted] = useState(false)
  const [currentJobs, setCurrentJobs] = useState<CreatorsSearchLocalJob[]>(() =>
    readCreatorsSearchJobs(),
  )
  const [expiredJobsError, setExpiredJobsError] = useState<string | null>(null)
  const [missingJobsError, setMissingJobsError] = useState<string | null>(null)
  const [reportError, setReportError] = useState<string | null>(null)
  const [searchError, setSearchError] = useState<string | null>(null)
  const [searchResult, setSearchResult] =
    useState<ProfileSnapshotExpandedCollection | null>(null)
  const [selectedSnapshot, setSelectedSnapshot] =
    useState<ProfileSnapshotExpanded | null>(null)
  const [selectedCurrentJobId, setSelectedCurrentJobId] = useState<
    string | null
  >(null)
  const reconcileJobsInFlightRef = useRef(false)
  const pageTopRef = useRef<HTMLDivElement | null>(null)

  const invalidUsernames = useMemo(
    () => usernames.filter((username) => !isValidInstagramUsername(username)),
    [usernames],
  )
  const invalidSet = useMemo(
    () => new Set(invalidUsernames),
    [invalidUsernames],
  )
  const isSearchStale = useMemo(
    () =>
      submittedUsernames.length > 0 &&
      !areStringArraysEqual(usernames, submittedUsernames),
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
  const selectedCurrentJob = useMemo(
    () =>
      selectedCurrentJobId
        ? (currentJobs.find((job) => job.jobId === selectedCurrentJobId) ??
          null)
        : null,
    [currentJobs, selectedCurrentJobId],
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
  const searchHistoryPreviewQuery = useQuery({
    queryKey: creatorsSearchHistoryQueryKey(SEARCH_HISTORY_PREVIEW_LIMIT),
    queryFn: () =>
      CreatorsSearchHistoryService.listCreatorsSearchHistory({
        limit: SEARCH_HISTORY_PREVIEW_LIMIT,
      }),
    staleTime: 30_000,
  })
  const searchHistoryViewAllQuery = useQuery({
    queryKey: creatorsSearchHistoryQueryKey(SEARCH_HISTORY_VIEW_ALL_LIMIT),
    queryFn: () =>
      CreatorsSearchHistoryService.listCreatorsSearchHistory({
        limit: SEARCH_HISTORY_VIEW_ALL_LIMIT,
      }),
    staleTime: 30_000,
    enabled: isSearchHistoryOpen,
  })

  const persistSearchHistoryEntryMutation = useMutation({
    mutationFn: (requestBody: CreatorsSearchHistoryCreateRequest) =>
      CreatorsSearchHistoryService.createCreatorsSearchHistoryEntry({
        requestBody,
      }),
    onSuccess: () => {
      void queryClient.invalidateQueries({
        queryKey: ["creators-search-history"],
      })
    },
    onError: (error) => {
      console.error("Unable to persist creators search history entry.", error)
    },
  })

  const persistSearchHistoryEntry = useCallback(
    (payload: CreatorsSearchHistoryCreateRequest) => {
      if (payload.ready_usernames.length === 0) {
        return
      }

      persistSearchHistoryEntryMutation.mutate(payload)
    },
    [persistSearchHistoryEntryMutation.mutate],
  )

  const reconcileCurrentJobs = useCallback(
    async (trigger: string) => {
      if (reconcileJobsInFlightRef.current) {
        return
      }

      const jobsToReconcile = readCreatorsSearchJobs().filter(
        (job) => job.status === "queued" || job.terminalPayload === null,
      )
      if (jobsToReconcile.length === 0) {
        return
      }

      reconcileJobsInFlightRef.current = true

      try {
        if (import.meta.env.DEV) {
          console.debug("[creators-search] reconciling jobs", {
            count: jobsToReconcile.length,
            jobIds: jobsToReconcile.map((job) => job.jobId),
            trigger,
          })
        }

        for (const job of jobsToReconcile) {
          try {
            const response = await InstagramService.getInstagramScrapeJob({
              jobId: job.jobId,
            })
            if (response.status === "done") {
              const readyUsernames =
                buildTerminalPayloadFromJobStatus(
                  response,
                  job.requestedUsernames,
                )?.ready_usernames ??
                getReadyUsernamesFromSummary(response.summary)
              if (readyUsernames.length > 0) {
                persistSearchHistoryEntry({
                  source: "ig-scrape-job",
                  job_id: response.job_id,
                  ready_usernames: readyUsernames,
                })
              }
            }
            updateCreatorsSearchJob(job.jobId, (currentJob) =>
              syncLocalJobWithStatusResponse(currentJob, response),
            )
          } catch (error) {
            if (error instanceof ApiError && error.status === 404) {
              removeCreatorsSearchJob(job.jobId)
            }
          }
        }
      } finally {
        reconcileJobsInFlightRef.current = false
      }
    },
    [persistSearchHistoryEntry],
  )

  const enqueueScrapeJobs = async (
    sourceBox: CreatorsSearchJobSourceBox,
    requestedUsernames: string[],
  ) => {
    const batches = createBalancedUsernameBatches(requestedUsernames)
    let createdCount = 0
    let skippedCount = 0

    for (const batch of batches) {
      const batchKey = buildCreatorsSearchBatchKey(sourceBox, batch)
      if (hasActiveCreatorsSearchJob(batchKey)) {
        skippedCount += 1
        continue
      }

      const token = localStorage.getItem("access_token") || ""
      const rawResponse = await fetch(
        `${OpenAPI.BASE}/api/v1/ig-scraper/jobs/apify`,
        {
          method: "POST",
          headers: {
            Authorization: `Bearer ${token}`,
            "Content-Type": "application/json",
            Accept: "application/json",
            "Idempotency-Key": createIdempotencyKey(),
          },
          body: JSON.stringify({
            usernames: batch,
          }),
        },
      )
      if (rawResponse.status === 401) {
        localStorage.removeItem("access_token")
        window.location.href = "/login"
        throw new Error("Your session has expired. Please log in again.")
      }
      if (!rawResponse.ok) {
        const errorBody = (await rawResponse.json().catch(() => ({}))) as {
          detail?: string
        }
        throw new Error(errorBody.detail || "Unable to create scrape job.")
      }
      const response = (await rawResponse.json()) as {
        job_id: string
        status: CreatorsSearchJobStatus
      }
      const now = new Date().toISOString()

      upsertCreatorsSearchJob({
        jobId: response.job_id,
        sourceBox,
        requestedUsernames: batch,
        batchKey,
        status: response.status,
        createdAt: now,
        updatedAt: now,
        readyUsernames: [],
        error: null,
        terminalPayload: null,
      })
      createdCount += 1
    }

    return {
      batchCount: batches.length,
      createdCount,
      skippedCount,
    }
  }

  const searchMutation = useMutation({
    mutationFn: (requestedUsernames: string[]) =>
      IgProfileSnapshotsService.readIgProfileSnapshotsAdvanced({
        limit: MAX_USERNAMES,
        usernames: requestedUsernames,
      }),
    onMutate: (requestedUsernames) => {
      setReportError(null)
      setExpiredJobsError(null)
      setMissingJobsError(null)
      setSubmittedUsernames(requestedUsernames)
      setSearchError(null)
      setSearchResult(null)
      setSelectedSnapshot(null)
    },
    onSuccess: (data, requestedUsernames) => {
      setSearchResult(data)
      const readyUsernames = getReadyUsernamesFromSearchResult(
        requestedUsernames,
        data,
      )
      if (readyUsernames.length > 0) {
        persistSearchHistoryEntry({
          source: "direct-search",
          ready_usernames: readyUsernames,
        })
      }
    },
    onError: (error) => {
      setSearchError(
        extractApiErrorMessage(error, "Unable to complete the search."),
      )
    },
  })

  const reportMutation = useMutation({
    mutationFn: generateInstagramReportPdf,
    onMutate: () => {
      setReportError(null)
    },
    onSuccess: () => {
      invalidateBillingSummary(queryClient)
    },
    onError: (error) => {
      setReportError(
        extractApiErrorMessage(error, "Unable to generate the report."),
      )
    },
  })

  const expiredJobsMutation = useMutation({
    mutationFn: (requestedUsernames: string[]) =>
      enqueueScrapeJobs("expired", requestedUsernames),
    onMutate: () => {
      setExpiredJobsError(null)
    },
    onSuccess: ({ batchCount, createdCount, skippedCount }) => {
      if (batchCount > 0 && createdCount === 0 && skippedCount === batchCount) {
        setExpiredJobsError(
          "An active scrape job already exists for these usernames.",
        )
      }

      scrollPageTopIntoView(pageTopRef)
    },
    onError: (error) => {
      setExpiredJobsError(
        extractApiErrorMessage(error, "Unable to create scrape jobs."),
      )
      scrollPageTopIntoView(pageTopRef)
    },
  })

  const missingJobsMutation = useMutation({
    mutationFn: (requestedUsernames: string[]) =>
      enqueueScrapeJobs("missing", requestedUsernames),
    onMutate: () => {
      setMissingJobsError(null)
    },
    onSuccess: ({ batchCount, createdCount, skippedCount }) => {
      if (batchCount > 0 && createdCount === 0 && skippedCount === batchCount) {
        setMissingJobsError(
          "An active scrape job already exists for these usernames.",
        )
      }

      scrollPageTopIntoView(pageTopRef)
    },
    onError: (error) => {
      setMissingJobsError(
        extractApiErrorMessage(error, "Unable to create scrape jobs."),
      )
      scrollPageTopIntoView(pageTopRef)
    },
  })

  useEffect(() => subscribeToCreatorsSearchJobs(setCurrentJobs), [])

  useEffect(() => {
    const handleUserEvent = (event: UserEvent) => {
      if (isIgScrapeJobCompletedEvent(event)) {
        if (event.envelope.payload.ready_usernames.length > 0) {
          persistSearchHistoryEntry({
            source: "ig-scrape-job",
            job_id: event.envelope.payload.job_id,
            ready_usernames: event.envelope.payload.ready_usernames,
          })
        }
        updateCreatorsSearchJob(event.envelope.payload.job_id, (job) => ({
          ...job,
          status: "done",
          updatedAt: event.envelope.payload.completed_at,
          readyUsernames: event.envelope.payload.ready_usernames,
          error: event.envelope.payload.error,
          terminalPayload: event.envelope.payload,
        }))
        return
      }

      if (isIgScrapeJobFailedEvent(event)) {
        updateCreatorsSearchJob(event.envelope.payload.job_id, (job) => ({
          ...job,
          status: "failed",
          updatedAt: event.envelope.payload.completed_at,
          readyUsernames: event.envelope.payload.ready_usernames,
          error: event.envelope.payload.error,
          terminalPayload: event.envelope.payload,
        }))
      }
    }

    return subscribeToUserEvents(handleUserEvent)
  }, [persistSearchHistoryEntry])

  useEffect(() => {
    void reconcileCurrentJobs("mount")

    const handleVisibilityChange = () => {
      if (document.visibilityState === "visible") {
        void reconcileCurrentJobs("visibility")
      }
    }

    const handleOnline = () => {
      void reconcileCurrentJobs("online")
    }

    document.addEventListener("visibilitychange", handleVisibilityChange)
    window.addEventListener("online", handleOnline)

    return () => {
      document.removeEventListener("visibilitychange", handleVisibilityChange)
      window.removeEventListener("online", handleOnline)
    }
  }, [reconcileCurrentJobs])

  const handleUsernamesChange = (nextValue: string[]) => {
    const sanitizedValue = sanitizeInstagramUsernames(nextValue)
    setUsernames(sanitizedValue)

    if (sanitizedValue.length < MAX_USERNAMES) {
      setOverflowAttempted(false)
    }
  }

  const handleSearch = () => {
    const nextUsernames = sanitizeInstagramUsernames(usernames)
    const nextInvalidUsernames = nextUsernames.filter(
      (username) => !isValidInstagramUsername(username),
    )

    setUsernames(nextUsernames)
    setOverflowAttempted(false)

    if (nextUsernames.length === 0 || nextInvalidUsernames.length > 0) {
      return
    }

    searchMutation.mutate(nextUsernames)
  }

  const handleReuseReadyUsernames = (readyUsernames: string[]) => {
    setUsernames(sanitizeInstagramUsernames(readyUsernames))
    setOverflowAttempted(false)
    setSelectedCurrentJobId(null)
    setIsSearchHistoryOpen(false)
  }

  return (
    <Box ref={pageTopRef} minH="100vh" bg="ui.page">
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

        <Grid
          templateColumns={{
            base: "1fr",
            "2xl": "minmax(0, 3fr) minmax(320px, 1fr)",
          }}
          gap={6}
          mb={{ base: 7, lg: 8 }}
        >
          <Box
            layerStyle="dashboardCard"
            p={{ base: 5, md: 6, lg: 7 }}
            display="flex"
            flexDirection="column"
            h="100%"
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
              <Flex mt={2} alignItems="center" gap={2} wrap="wrap">
                <Heading size="lg">Search creators by username</Heading>
                <Tooltip.Root
                  openDelay={160}
                  positioning={{ placement: "top" }}
                >
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
              flex="1"
              label="Instagram usernames"
              helperText={
                hasValidationIssue
                  ? undefined
                  : "Up to 50 usernames per request."
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
              alignItems={{ base: "stretch", md: "center" }}
              justifyContent="space-between"
              gap={3}
              direction={{ base: "column", md: "row" }}
              mt="auto"
              pt={6}
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
                alignSelf={{ base: "stretch", md: "flex-start" }}
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

          <Box layerStyle="dashboardCard" p={{ base: 6, md: 8 }}>
            <Text
              fontSize="sm"
              color="ui.mutedText"
              fontWeight="bold"
              letterSpacing="0.08em"
            >
              CURRENT JOBS
            </Text>
            <Flex
              mt={2}
              alignItems="center"
              justifyContent="space-between"
              gap={3}
            >
              <Heading size="md">Mining for creators.</Heading>
              <Badge
                rounded="full"
                borderWidth="1px"
                borderColor="ui.borderSoft"
                bg="ui.surfaceSoft"
                color="ui.secondaryText"
                px={3}
                py={1.5}
              >
                {currentJobs.length} / 10 jobs
              </Badge>
            </Flex>
            <Text mt={3} color="ui.secondaryText" fontSize="sm">
              Active and recent scrape jobs are kept locally on this browser.
            </Text>

            <Flex
              mt={5}
              direction="column"
              gap={3}
              maxH="560px"
              overflowY="auto"
              pr={1}
            >
              {currentJobs.length === 0 ? (
                <Box
                  rounded="2xl"
                  borderWidth="1px"
                  borderColor="ui.border"
                  bg="ui.surfaceSoft"
                  px={4}
                  py={4}
                >
                  <Text
                    color="ui.secondaryText"
                    fontSize="sm"
                    fontWeight="bold"
                  >
                    No scrape jobs yet.
                  </Text>
                </Box>
              ) : (
                currentJobs.map((job) => {
                  const statusStyles = getJobStatusStyles(job.status)
                  const visibleUsernames = job.requestedUsernames.slice(0, 5)
                  const hiddenUsernamesCount = Math.max(
                    job.requestedUsernames.length - visibleUsernames.length,
                    0,
                  )
                  const canOpenDetail =
                    (job.status === "done" || job.status === "failed") &&
                    (job.terminalPayload !== null ||
                      job.readyUsernames.length > 0 ||
                      Boolean(job.error))

                  return (
                    <Box
                      key={job.jobId}
                      as={canOpenDetail ? "button" : "div"}
                      rounded="2xl"
                      borderWidth="1px"
                      borderColor={statusStyles.borderColor}
                      bg={statusStyles.bg}
                      px={4}
                      py={4}
                      textAlign="left"
                      transition="transform 180ms ease, box-shadow 180ms ease"
                      cursor={canOpenDetail ? "pointer" : "default"}
                      _hover={
                        canOpenDetail
                          ? {
                              boxShadow: "md",
                            }
                          : undefined
                      }
                      onClick={
                        canOpenDetail
                          ? () => setSelectedCurrentJobId(job.jobId)
                          : undefined
                      }
                    >
                      <Flex
                        alignItems="flex-start"
                        justifyContent="space-between"
                        gap={3}
                      >
                        <Box minW={0}>
                          <Text
                            color={statusStyles.textColor}
                            fontSize="xs"
                            fontWeight="black"
                            lineClamp={2}
                          >
                            {job.jobId}
                          </Text>
                        </Box>

                        <Badge
                          rounded="full"
                          borderWidth="1px"
                          borderColor="rgba(255,255,255,0.18)"
                          bg="ui.panel"
                          color={statusStyles.textColor}
                          px={3}
                          py={1.5}
                        >
                          {getJobStatusLabel(job.status)}
                        </Badge>
                      </Flex>

                      <Flex mt={3} gap={2} wrap="wrap">
                        {visibleUsernames.map((username) => (
                          <Badge
                            key={`${job.jobId}-${username}`}
                            rounded="full"
                            borderWidth="1px"
                            borderColor="ui.borderSoft"
                            bg="ui.panel"
                            color="ui.text"
                            px={2.0}
                            py={0.5}
                            fontSize="2xs"
                          >
                            @{username}
                          </Badge>
                        ))}
                        {hiddenUsernamesCount > 0 ? (
                          <Badge
                            rounded="full"
                            borderWidth="1px"
                            borderColor="ui.borderSoft"
                            bg="ui.panel"
                            color="ui.secondaryText"
                            px={2.5}
                            py={1}
                            fontSize="xs"
                          >
                            +{hiddenUsernamesCount}
                          </Badge>
                        ) : null}
                      </Flex>

                      {job.error ? (
                        <Text
                          mt={3}
                          color={statusStyles.textColor}
                          fontSize="sm"
                        >
                          {job.error}
                        </Text>
                      ) : null}

                      <Text mt={3} color="ui.secondaryText" fontSize="sm">
                        {canOpenDetail
                          ? "Click to review the terminal result."
                          : "Waiting for completion."}
                      </Text>
                    </Box>
                  )
                })
              )}
            </Flex>
          </Box>
        </Grid>

        <Box
          layerStyle="dashboardCard"
          p={{ base: 6, md: 8 }}
          mb={{ base: 7, lg: 8 }}
        >
          <Flex
            alignItems={{ base: "flex-start", md: "center" }}
            justifyContent="space-between"
            gap={4}
            direction={{ base: "column", md: "row" }}
          >
            <Box>
              <Text
                fontSize="sm"
                color="ui.mutedText"
                fontWeight="bold"
                letterSpacing="0.08em"
              >
                SEARCH HISTORY
              </Text>
              <Heading mt={2} size="md">
                Search history
              </Heading>
              <Text mt={2} color="ui.secondaryText">
                Keep the last ready username lists one click away.
              </Text>
            </Box>

            {searchHistoryPreviewQuery.data?.items?.length ? (
              <Button
                variant="outline"
                alignSelf={{ base: "stretch", md: "flex-start" }}
                onClick={() => setIsSearchHistoryOpen(true)}
              >
                View all
              </Button>
            ) : null}
          </Flex>

          {searchHistoryPreviewQuery.isLoading ? (
            <Flex mt={5} direction="column" gap={3}>
              <ResultSkeletonCard />
            </Flex>
          ) : searchHistoryPreviewQuery.isError ? (
            <Box
              mt={5}
              rounded="2xl"
              borderWidth="1px"
              borderColor="ui.border"
              bg="ui.surfaceSoft"
              px={4}
              py={4}
            >
              <Text color="ui.secondaryText" fontSize="sm" fontWeight="bold">
                Search history is temporarily unavailable.
              </Text>
            </Box>
          ) : (searchHistoryPreviewQuery.data?.items?.length ?? 0) === 0 ? (
            <Box
              mt={5}
              rounded="2xl"
              borderWidth="1px"
              borderColor="ui.border"
              bg="ui.surfaceSoft"
              px={4}
              py={4}
            >
              <Text color="ui.secondaryText" fontSize="sm" fontWeight="bold">
                No search history available yet.
              </Text>
            </Box>
          ) : (
            <Box mt={7} overflowX="auto" overflowY="hidden" pb={2}>
              <Box
                display="grid"
                gridAutoFlow="column"
                gridAutoColumns={{
                  base: "minmax(220px, 85%)",
                  md: "minmax(210px, calc((100% - 2rem) / 3))",
                  lg: "minmax(200px, calc((100% - 3rem) / 4))",
                  xl: "minmax(190px, calc((100% - 4rem) / 5))",
                }}
                gap={4}
                alignItems="stretch"
              >
                {(searchHistoryPreviewQuery.data?.items ?? []).map((item) => (
                  <SearchHistoryCard
                    key={item.id}
                    compact
                    item={item}
                    onClick={handleReuseReadyUsernames}
                  />
                ))}
              </Box>
            </Box>
          )}
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
              label="Update Needed"
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
              Profiles need updates
            </Text>
            <Flex
              mt={2}
              alignItems={{ base: "stretch", md: "flex-start" }}
              justifyContent="space-between"
              gap={3}
              direction={{ base: "column", md: "row" }}
            >
              <Text color="ui.secondaryText">
                These creators exist in saved data, but their stored profile
                data needs to be updated. They are highlighted in yellow above
                and in the results list so you can identify which saved profiles
                need to be refreshed.
              </Text>
              <Button
                flexShrink={0}
                loading={expiredJobsMutation.isPending}
                onClick={() => expiredJobsMutation.mutate(expiredUsernames)}
                disabled={
                  expiredUsernames.length === 0 || expiredJobsMutation.isPending
                }
              >
                <FiSearch />
                Search
              </Button>
            </Flex>

            {expiredJobsError ? (
              <Text
                mt={3}
                color="ui.warningText"
                fontSize="sm"
                fontWeight="bold"
              >
                {expiredJobsError}
              </Text>
            ) : null}

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
            <Flex
              mt={2}
              alignItems={{ base: "stretch", md: "flex-start" }}
              justifyContent="space-between"
              gap={3}
              direction={{ base: "column", md: "row" }}
            >
              <Text color="ui.secondaryText" maxW="56ch">
                These usernames were not found in the saved creator data. They
                are also highlighted in red above.
              </Text>
              <Button
                flexShrink={0}
                loading={missingJobsMutation.isPending}
                onClick={() => missingJobsMutation.mutate(missingUsernames)}
                disabled={
                  missingUsernames.length === 0 || missingJobsMutation.isPending
                }
              >
                <FiSearch />
                Search
              </Button>
            </Flex>

            {missingJobsError ? (
              <Text
                mt={3}
                color="ui.dangerText"
                fontSize="sm"
                fontWeight="bold"
              >
                {missingJobsError}
              </Text>
            ) : null}

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
        ) : null}
      </Box>

      <CreatorSnapshotDetailDialog
        snapshot={selectedSnapshot}
        onOpenChange={(open) => {
          if (!open) {
            setSelectedSnapshot(null)
          }
        }}
      />
      <CurrentJobDetailDialog
        job={selectedCurrentJob}
        onOpenChange={(open) => {
          if (!open) {
            setSelectedCurrentJobId(null)
          }
        }}
        onReuseReadyUsernames={handleReuseReadyUsernames}
      />
      <SearchHistoryViewAllDialog
        items={searchHistoryViewAllQuery.data?.items ?? []}
        loading={searchHistoryViewAllQuery.isLoading}
        open={isSearchHistoryOpen}
        onOpenChange={setIsSearchHistoryOpen}
        onReuseReadyUsernames={handleReuseReadyUsernames}
      />
      <SearchGuideDialog open={isGuideOpen} onOpenChange={setIsGuideOpen} />
    </Box>
  )
}
