import type { QueryClient } from "@tanstack/react-query"
import { useMutation } from "@tanstack/react-query"
import { useState } from "react"

import { invalidateBillingSummary } from "@/features/billing/api"
import { extractApiErrorMessage } from "@/lib/api-errors"

import { generateInstagramReportPdf } from "./creators-search.api"

export const useCreatorReport = ({
  queryClient,
}: {
  queryClient: QueryClient
}) => {
  const [reportError, setReportError] = useState<string | null>(null)

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

  return {
    clearReportError: () => setReportError(null),
    reportError,
    reportMutation,
  }
}
