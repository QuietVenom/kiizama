import { useMutation } from "@tanstack/react-query"
import {
  type RefObject,
  useCallback,
  useEffect,
  useMemo,
  useRef,
  useState,
} from "react"
import { useTranslation } from "react-i18next"

import {
  ApiError,
  type CreatorsSearchHistoryCreateRequest,
  InstagramService,
} from "@/client"
import { subscribeToUserEvents } from "@/features/user-events/connection"
import {
  isIgScrapeJobCompletedEvent,
  isIgScrapeJobFailedEvent,
  type UserEvent,
} from "@/features/user-events/types"
import { extractApiErrorMessage } from "@/lib/api-errors"
import {
  buildTerminalPayloadFromJobStatus,
  type CreatorsSearchLocalJob,
  getReadyUsernamesFromSummary,
  readCreatorsSearchJobs,
  removeCreatorsSearchJob,
  subscribeToCreatorsSearchJobs,
  syncLocalJobWithStatusResponse,
  updateCreatorsSearchJob,
} from "@/lib/creators-search-jobs"

import { enqueueCreatorsSearchScrapeJobs } from "./creators-search.api"

const scrollPageTopIntoView = (targetRef: RefObject<HTMLElement | null>) => {
  targetRef.current?.scrollIntoView({ behavior: "smooth", block: "start" })
}

export const useCreatorsSearchJobs = ({
  pageTopRef,
  persistSearchHistoryEntry,
}: {
  pageTopRef: RefObject<HTMLElement | null>
  persistSearchHistoryEntry: (
    payload: CreatorsSearchHistoryCreateRequest,
  ) => void
}) => {
  const { t } = useTranslation("creatorsSearch")
  const [currentJobs, setCurrentJobs] = useState<CreatorsSearchLocalJob[]>(() =>
    readCreatorsSearchJobs(),
  )
  const [expiredJobsError, setExpiredJobsError] = useState<string | null>(null)
  const [missingJobsError, setMissingJobsError] = useState<string | null>(null)
  const [selectedCurrentJobId, setSelectedCurrentJobId] = useState<
    string | null
  >(null)
  const reconcileJobsInFlightRef = useRef(false)

  const selectedCurrentJob = useMemo(
    () =>
      selectedCurrentJobId
        ? (currentJobs.find((job) => job.jobId === selectedCurrentJobId) ??
          null)
        : null,
    [currentJobs, selectedCurrentJobId],
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

  const expiredJobsMutation = useMutation({
    mutationFn: (requestedUsernames: string[]) =>
      enqueueCreatorsSearchScrapeJobs("expired", requestedUsernames),
    onMutate: () => {
      setExpiredJobsError(null)
    },
    onSuccess: ({ batchCount, createdCount, skippedCount }) => {
      if (batchCount > 0 && createdCount === 0 && skippedCount === batchCount) {
        setExpiredJobsError(t("jobs.errors.duplicateActiveJob"))
      }

      scrollPageTopIntoView(pageTopRef)
    },
    onError: (error) => {
      setExpiredJobsError(
        extractApiErrorMessage(error, t("jobs.errors.unableToCreate")),
      )
      scrollPageTopIntoView(pageTopRef)
    },
  })

  const missingJobsMutation = useMutation({
    mutationFn: (requestedUsernames: string[]) =>
      enqueueCreatorsSearchScrapeJobs("missing", requestedUsernames),
    onMutate: () => {
      setMissingJobsError(null)
    },
    onSuccess: ({ batchCount, createdCount, skippedCount }) => {
      if (batchCount > 0 && createdCount === 0 && skippedCount === batchCount) {
        setMissingJobsError(t("jobs.errors.duplicateActiveJob"))
      }

      scrollPageTopIntoView(pageTopRef)
    },
    onError: (error) => {
      setMissingJobsError(
        extractApiErrorMessage(error, t("jobs.errors.unableToCreate")),
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

  return {
    clearJobErrors: () => {
      setExpiredJobsError(null)
      setMissingJobsError(null)
    },
    clearSelectedCurrentJob: () => setSelectedCurrentJobId(null),
    currentJobs,
    expiredJobsError,
    expiredJobsMutation,
    missingJobsError,
    missingJobsMutation,
    selectCurrentJob: setSelectedCurrentJobId,
    selectedCurrentJob,
  }
}
