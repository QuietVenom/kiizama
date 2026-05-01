import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import { useCallback } from "react"

import {
  type CreatorsSearchHistoryCreateRequest,
  CreatorsSearchHistoryService,
} from "@/client"

import {
  creatorsSearchHistoryQueryKey,
  SEARCH_HISTORY_PREVIEW_LIMIT,
  SEARCH_HISTORY_VIEW_ALL_LIMIT,
} from "./creators-search.logic"

export const useCreatorsSearchHistory = ({
  isViewAllOpen,
}: {
  isViewAllOpen: boolean
}) => {
  const queryClient = useQueryClient()
  const previewQuery = useQuery({
    queryKey: creatorsSearchHistoryQueryKey(SEARCH_HISTORY_PREVIEW_LIMIT),
    queryFn: () =>
      CreatorsSearchHistoryService.listCreatorsSearchHistory({
        limit: SEARCH_HISTORY_PREVIEW_LIMIT,
      }),
    staleTime: 30_000,
  })
  const viewAllQuery = useQuery({
    queryKey: creatorsSearchHistoryQueryKey(SEARCH_HISTORY_VIEW_ALL_LIMIT),
    queryFn: () =>
      CreatorsSearchHistoryService.listCreatorsSearchHistory({
        limit: SEARCH_HISTORY_VIEW_ALL_LIMIT,
      }),
    staleTime: 30_000,
    enabled: isViewAllOpen,
  })

  const persistMutation = useMutation({
    mutationFn: (requestBody: CreatorsSearchHistoryCreateRequest) =>
      CreatorsSearchHistoryService.createCreatorsSearchHistoryEntry({
        requestBody,
      }),
    onSuccess: () => {
      void queryClient.invalidateQueries({
        queryKey: creatorsSearchHistoryQueryKey(),
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

      persistMutation.mutate(payload)
    },
    [persistMutation.mutate],
  )

  return {
    persistSearchHistoryEntry,
    previewQuery,
    viewAllQuery,
  }
}
