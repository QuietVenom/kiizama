import { Box, Grid, SimpleGrid } from "@chakra-ui/react"
import { useMutation, useQueryClient } from "@tanstack/react-query"
import { useMemo, useRef, useState } from "react"
import { useTranslation } from "react-i18next"

import {
  IgProfileSnapshotsService,
  type ProfileSnapshotExpanded,
  type ProfileSnapshotExpandedCollection,
} from "@/client"
import CreatorSnapshotDetailDialog from "@/components/CreatorsSearch/CreatorSnapshotDetailDialog"
import { extractApiErrorMessage } from "@/lib/api-errors"
import {
  areStringArraysEqual,
  isValidInstagramUsername,
  sanitizeInstagramUsernames,
} from "@/lib/instagram-usernames"

import { CurrentJobDetailDialog } from "./CurrentJobDetailDialog"
import { CurrentJobsPanel } from "./CurrentJobsPanel"
import {
  getReadyUsernamesFromSearchResult,
  getValidationMessage,
  MAX_USERNAMES,
  sortSnapshotsByUsernames,
} from "./creators-search.logic"
import { SearchHistoryDialog } from "./SearchHistoryDialog"
import { SearchHistoryPanel } from "./SearchHistoryPanel"
import { SearchInputPanel } from "./SearchInputPanel"
import { SearchOutcomeAlerts } from "./SearchOutcomeAlerts"
import { SearchOverviewCard } from "./SearchOverviewCard"
import { SearchResultsSection } from "./SearchResultsSection"
import { useCreatorReport } from "./useCreatorReport"
import { useCreatorsSearchHistory } from "./useCreatorsSearchHistory"
import { useCreatorsSearchJobs } from "./useCreatorsSearchJobs"

export function DirectCreatorsSearchTab() {
  const { t } = useTranslation("creatorsSearch")
  const queryClient = useQueryClient()
  const [isSearchHistoryOpen, setIsSearchHistoryOpen] = useState(false)
  const [usernames, setUsernames] = useState<string[]>([])
  const [submittedUsernames, setSubmittedUsernames] = useState<string[]>([])
  const [overflowAttempted, setOverflowAttempted] = useState(false)
  const [searchError, setSearchError] = useState<string | null>(null)
  const [searchResult, setSearchResult] =
    useState<ProfileSnapshotExpandedCollection | null>(null)
  const [selectedSnapshot, setSelectedSnapshot] =
    useState<ProfileSnapshotExpanded | null>(null)
  const [isCurrentJobsCollapsed, setIsCurrentJobsCollapsed] = useState(true)
  const [isSearchHistoryCollapsed, setIsSearchHistoryCollapsed] = useState(true)
  const pageTopRef = useRef<HTMLDivElement | null>(null)

  const { persistSearchHistoryEntry, previewQuery, viewAllQuery } =
    useCreatorsSearchHistory({
      isViewAllOpen: isSearchHistoryOpen,
    })
  const {
    clearJobErrors,
    clearSelectedCurrentJob,
    currentJobs,
    expiredJobsError,
    expiredJobsMutation,
    missingJobsError,
    missingJobsMutation,
    selectCurrentJob,
    selectedCurrentJob,
  } = useCreatorsSearchJobs({
    onJobsEnqueued: () => setIsCurrentJobsCollapsed(false),
    pageTopRef,
    persistSearchHistoryEntry,
  })
  const { clearReportError, reportError, reportMutation } = useCreatorReport({
    queryClient,
  })

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

  const validationMessage = getValidationMessage(
    invalidUsernames,
    overflowAttempted,
    (key, options) => t(key, options),
  )
  const hasValidationIssue = Boolean(validationMessage)
  const hasSearched =
    submittedUsernames.length > 0 ||
    searchResult !== null ||
    searchError !== null
  const shouldShowCurrentJobsPanel = currentJobs.length > 0
  const historyItems = previewQuery.data?.items ?? []
  const shouldShowHistoryPanel = previewQuery.isError || historyItems.length > 0

  const searchMutation = useMutation({
    mutationFn: (requestedUsernames: string[]) =>
      IgProfileSnapshotsService.readIgProfileSnapshotsAdvanced({
        limit: MAX_USERNAMES,
        usernames: requestedUsernames,
      }),
    onMutate: (requestedUsernames) => {
      clearReportError()
      clearJobErrors()
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
      setSearchError(extractApiErrorMessage(error, t("alerts.searchFailed")))
    },
  })

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
    clearSelectedCurrentJob()
    setIsSearchHistoryOpen(false)
  }

  return (
    <Box ref={pageTopRef}>
      {shouldShowCurrentJobsPanel ? (
        <Box mb={{ base: 6, lg: 7 }}>
          <CurrentJobsPanel
            collapsed={isCurrentJobsCollapsed}
            currentJobs={currentJobs}
            onSelectJob={selectCurrentJob}
            onToggleCollapsed={() =>
              setIsCurrentJobsCollapsed((current) => !current)
            }
          />
        </Box>
      ) : null}

      {shouldShowHistoryPanel ? (
        <SearchHistoryPanel
          collapsed={isSearchHistoryCollapsed}
          isError={previewQuery.isError}
          isLoading={previewQuery.isLoading}
          items={historyItems}
          onReuseReadyUsernames={handleReuseReadyUsernames}
          onToggleCollapsed={() =>
            setIsSearchHistoryCollapsed((current) => !current)
          }
        />
      ) : null}

      <SearchOutcomeAlerts
        expiredJobsError={expiredJobsError}
        expiredJobsMutation={expiredJobsMutation}
        expiredUsernames={expiredUsernames}
        missingJobsError={missingJobsError}
        missingJobsMutation={missingJobsMutation}
        missingUsernames={missingUsernames}
        reportError={reportError}
        searchError={searchError}
      />

      {hasSearched && !searchMutation.isPending ? (
        <SimpleGrid
          columns={{ base: 1, md: 2, xl: 4 }}
          gap={5}
          mb={{ base: 6, lg: 7 }}
        >
          <SearchOverviewCard
            label={t("results.overview.requested")}
            tone="brand"
            value={String(submittedUsernames.length)}
          />
          <SearchOverviewCard
            label={t("results.overview.found", {
              count: sortedSnapshots.length,
            })}
            tone="success"
            value={String(sortedSnapshots.length)}
          />
          <SearchOverviewCard
            label={t("results.overview.updateNeeded")}
            tone="warning"
            value={String(expiredUsernames.length)}
          />
          <SearchOverviewCard
            label={t("results.overview.notFound")}
            tone="danger"
            value={String(missingUsernames.length)}
          />
        </SimpleGrid>
      ) : null}

      <Grid
        templateColumns={{
          base: "1fr",
          xl: "minmax(280px, 0.55fr) minmax(0, 1.75fr)",
        }}
        gap={6}
        alignItems="start"
      >
        <SearchInputPanel
          expiredSet={expiredSet}
          hasValidationIssue={hasValidationIssue}
          invalidSet={invalidSet}
          invalidUsernames={invalidUsernames}
          isSearchPending={searchMutation.isPending}
          isSearchStale={isSearchStale}
          maxUsernames={MAX_USERNAMES}
          missingSet={missingSet}
          usernames={usernames}
          validationMessage={validationMessage}
          onMaxExceeded={() => setOverflowAttempted(true)}
          onSearch={handleSearch}
          onUsernamesChange={handleUsernamesChange}
        />

        <SearchResultsSection
          expiredSet={expiredSet}
          hasSearched={hasSearched}
          isSearchPending={searchMutation.isPending}
          reportMutation={reportMutation}
          searchError={searchError}
          snapshots={sortedSnapshots}
          onOpenSnapshot={setSelectedSnapshot}
        />
      </Grid>

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
            clearSelectedCurrentJob()
          }
        }}
        onReuseReadyUsernames={handleReuseReadyUsernames}
      />
      <SearchHistoryDialog
        items={viewAllQuery.data?.items ?? []}
        loading={viewAllQuery.isLoading}
        open={isSearchHistoryOpen}
        onOpenChange={setIsSearchHistoryOpen}
        onReuseReadyUsernames={handleReuseReadyUsernames}
      />
    </Box>
  )
}

export default DirectCreatorsSearchTab
