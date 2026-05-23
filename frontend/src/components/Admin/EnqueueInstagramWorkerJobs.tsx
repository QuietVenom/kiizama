import {
  Badge,
  Box,
  Button,
  Flex,
  Heading,
  List,
  Text,
  Textarea,
  VStack,
} from "@chakra-ui/react"
import { useMutation, useQuery } from "@tanstack/react-query"
import { useMemo, useState } from "react"

import {
  type InstagramScrapeJobCreateResponse,
  InstagramService,
} from "@/client"
import type { ApiError } from "@/client/core/ApiError"
import { createIdempotencyKey } from "@/features/billing/api"
import { currentUserQueryOptions } from "@/hooks/useAuth"
import useCustomToast from "@/hooks/useCustomToast"
import { createBalancedUsernameBatches } from "@/lib/creators-search-jobs"
import {
  MAX_INSTAGRAM_USERNAMES,
  sanitizeInstagramUsernames,
} from "@/lib/instagram-usernames"
import { Field } from "../ui/field"

type CreatedBatchJob = {
  batchIndex: number
  jobId: string
  usernames: string[]
}

const parseApiErrorMessage = (error: unknown) => {
  if (error instanceof Error && error.message) {
    return error.message
  }
  return "Unable to enqueue Instagram scrape jobs."
}

const normalizeTextareaValue = (value: string) =>
  sanitizeInstagramUsernames(value.split(/[\s,]+/)).slice(
    0,
    MAX_INSTAGRAM_USERNAMES,
  )

const EnqueueInstagramWorkerJobs = () => {
  const [rawInput, setRawInput] = useState("")
  const [createdJobs, setCreatedJobs] = useState<CreatedBatchJob[]>([])
  const { data: currentUser } = useQuery(currentUserQueryOptions)
  const { showErrorToast, showSuccessToast } = useCustomToast()

  const normalizedUsernames = useMemo(
    () => normalizeTextareaValue(rawInput),
    [rawInput],
  )
  const batches = useMemo(
    () => createBalancedUsernameBatches(normalizedUsernames),
    [normalizedUsernames],
  )

  const mutation = useMutation({
    mutationFn: async (usernames: string[]) => {
      const results: CreatedBatchJob[] = []

      for (const [index, batch] of createBalancedUsernameBatches(
        usernames,
      ).entries()) {
        const response: InstagramScrapeJobCreateResponse =
          await InstagramService.createInstagramScrapeJob({
            requestBody: { usernames: batch },
            idempotencyKey: createIdempotencyKey(),
          })

        results.push({
          batchIndex: index + 1,
          jobId: response.job_id,
          usernames: batch,
        })
      }

      return results
    },
    onSuccess: (results) => {
      setCreatedJobs(results)
      showSuccessToast(
        results.length === 1
          ? "Instagram worker job created."
          : `${results.length} Instagram worker jobs created.`,
      )
    },
    onError: (error: ApiError | Error) => {
      showErrorToast(parseApiErrorMessage(error))
    },
  })

  if (!currentUser?.is_superuser) {
    return null
  }

  const isSubmitting = mutation.isPending

  return (
    <Box
      borderWidth="1px"
      borderColor="ui.border"
      bg="ui.surface"
      rounded="xl"
      p={{ base: 4, md: 5 }}
      mt={4}
    >
      <VStack align="stretch" gap={4}>
        <Box>
          <Heading size="md">Instagram Worker Jobs</Heading>
          <Text mt={1} color="ui.secondaryText" fontSize="sm">
            Send usernames directly to the worker job endpoint. Requests are
            normalized and balanced into batches of up to 10 usernames.
          </Text>
        </Box>

        <Field
          label="Instagram usernames"
          helperText={`${normalizedUsernames.length} / ${MAX_INSTAGRAM_USERNAMES} usernames`}
        >
          <Textarea
            value={rawInput}
            onChange={(event) => setRawInput(event.target.value)}
            minH="160px"
            placeholder="Paste usernames, commas, spaces, or Instagram profile URLs."
          />
        </Field>

        <Flex
          direction={{ base: "column", md: "row" }}
          align={{ base: "stretch", md: "center" }}
          justify="space-between"
          gap={3}
        >
          <Flex wrap="wrap" gap={2}>
            <Badge colorPalette="gray" variant="subtle">
              {batches.length} batches
            </Badge>
            <Badge colorPalette="gray" variant="subtle">
              Max 10 per batch
            </Badge>
          </Flex>
          <Button
            layerStyle="brandGradientButton"
            onClick={() => mutation.mutate(normalizedUsernames)}
            disabled={normalizedUsernames.length === 0 || isSubmitting}
            loading={isSubmitting}
          >
            Queue Worker Jobs
          </Button>
        </Flex>

        {createdJobs.length > 0 ? (
          <Box
            borderWidth="1px"
            borderColor="ui.border"
            bg="ui.surfaceSoft"
            rounded="lg"
            p={4}
          >
            <Text fontWeight="semibold" mb={3}>
              Created jobs
            </Text>
            <List.Root gap={2}>
              {createdJobs.map((job) => (
                <List.Item key={job.jobId} listStyleType="none">
                  <Text fontSize="sm">
                    Batch {job.batchIndex}: <strong>{job.jobId}</strong>
                  </Text>
                  <Text fontSize="sm" color="ui.secondaryText">
                    {job.usernames.join(", ")}
                  </Text>
                </List.Item>
              ))}
            </List.Root>
          </Box>
        ) : null}
      </VStack>
    </Box>
  )
}

export default EnqueueInstagramWorkerJobs
