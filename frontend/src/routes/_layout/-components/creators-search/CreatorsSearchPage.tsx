import { Box, Grid } from "@chakra-ui/react"
import { useMutation, useQueryClient } from "@tanstack/react-query"
import { useMemo, useRef, useState } from "react"

import {
  IgProfileSnapshotsService,
  type ProfileSnapshotExpanded,
  type ProfileSnapshotExpandedCollection,
} from "@/client"
import CreatorSnapshotDetailDialog from "@/components/CreatorsSearch/CreatorSnapshotDetailDialog"
import DashboardTopbar from "@/components/Dashboard/DashboardTopbar"
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
import { SearchGuideDialog } from "./SearchGuideDialog"
import { SearchHeader } from "./SearchHeader"
import { SearchHistoryDialog } from "./SearchHistoryDialog"
import { SearchHistoryPanel } from "./SearchHistoryPanel"
import { SearchInputPanel } from "./SearchInputPanel"
import { SearchOutcomeAlerts } from "./SearchOutcomeAlerts"
import { SearchResultsSection } from "./SearchResultsSection"
import { useCreatorReport } from "./useCreatorReport"
import { useCreatorsSearchHistory } from "./useCreatorsSearchHistory"
import { useCreatorsSearchJobs } from "./useCreatorsSearchJobs"

export function CreatorsSearchPage() {
  const queryClient = useQueryClient()
  const [isGuideOpen, setIsGuideOpen] = useState(false)
  const [isSearchHistoryOpen, setIsSearchHistoryOpen] = useState(false)
  const [usernames, setUsernames] = useState<string[]>([])
  const [submittedUsernames, setSubmittedUsernames] = useState<string[]>([])
  const [overflowAttempted, setOverflowAttempted] = useState(false)
  const [searchError, setSearchError] = useState<string | null>(null)
  const [searchResult, setSearchResult] =
    useState<ProfileSnapshotExpandedCollection | null>(null)
  const [selectedSnapshot, setSelectedSnapshot] =
    useState<ProfileSnapshotExpanded | null>(null)
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
      setSearchError(
        extractApiErrorMessage(error, "Unable to complete the search."),
      )
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
    <Box ref={pageTopRef} minH="100vh" bg="ui.page">
      <DashboardTopbar />

      <Box px={{ base: 4, md: 7, lg: 10 }} py={{ base: 7, lg: 9 }}>
        <SearchHeader onOpenGuide={() => setIsGuideOpen(true)} />

        <Grid
          templateColumns={{
            base: "1fr",
            "2xl": "minmax(0, 3fr) minmax(320px, 1fr)",
          }}
          gap={6}
          mb={{ base: 7, lg: 8 }}
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

          <CurrentJobsPanel
            currentJobs={currentJobs}
            onSelectJob={selectCurrentJob}
          />
        </Grid>

        <SearchHistoryPanel
          isError={previewQuery.isError}
          isLoading={previewQuery.isLoading}
          items={previewQuery.data?.items ?? []}
          onReuseReadyUsernames={handleReuseReadyUsernames}
          onViewAll={() => setIsSearchHistoryOpen(true)}
        />

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

        <SearchResultsSection
          expiredSet={expiredSet}
          expiredUsernames={expiredUsernames}
          hasSearched={hasSearched}
          isSearchPending={searchMutation.isPending}
          missingUsernames={missingUsernames}
          reportMutation={reportMutation}
          searchError={searchError}
          snapshots={sortedSnapshots}
          submittedUsernames={submittedUsernames}
          onOpenSnapshot={setSelectedSnapshot}
        />
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
      <SearchGuideDialog open={isGuideOpen} onOpenChange={setIsGuideOpen} />
    </Box>
  )
}
