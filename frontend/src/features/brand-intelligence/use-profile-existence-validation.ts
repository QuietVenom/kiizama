import { useMutation } from "@tanstack/react-query"
import { useCallback, useEffect, useMemo, useState } from "react"

import type { ProfileExistenceCollection } from "@/client"
import { extractApiErrorMessage } from "@/lib/api-errors"
import { areStringArraysEqual } from "@/lib/instagram-usernames"

import { readProfilesExistence } from "./api"
import { orderProfileExistence } from "./utils"

export const useProfileExistenceValidation = (currentUsernames: string[]) => {
  const [validatedUsernames, setValidatedUsernames] = useState<string[]>([])
  const [result, setResult] = useState<ProfileExistenceCollection | null>(null)
  const [validationError, setValidationError] = useState<string | null>(null)
  const hasCurrentUsernames = currentUsernames.length > 0

  const resetValidationState = useCallback(() => {
    setValidatedUsernames((previousUsernames) =>
      previousUsernames.length === 0 ? previousUsernames : [],
    )
    setResult((previousResult) =>
      previousResult === null ? previousResult : null,
    )
    setValidationError((previousError) =>
      previousError === null ? previousError : null,
    )
  }, [])

  useEffect(() => {
    if (!hasCurrentUsernames) {
      resetValidationState()
    }
  }, [hasCurrentUsernames, resetValidationState])

  const validationMutation = useMutation({
    mutationFn: (requestedUsernames: string[]) =>
      readProfilesExistence(requestedUsernames),
    onMutate: () => {
      setValidationError(null)
    },
    onSuccess: (data, requestedUsernames) => {
      setValidatedUsernames(requestedUsernames)
      setResult(data)
    },
    onError: (error) => {
      setValidationError(
        extractApiErrorMessage(
          error,
          "Unable to validate the selected profiles.",
        ),
      )
    },
  })

  const isValidationStale =
    validatedUsernames.length > 0 &&
    !areStringArraysEqual(currentUsernames, validatedUsernames)

  const hasValidatedProfiles =
    validatedUsernames.length > 0 && result !== null && !isValidationStale

  const orderedProfiles = useMemo(
    () =>
      !hasValidatedProfiles
        ? []
        : orderProfileExistence(currentUsernames, result?.profiles ?? []),
    [currentUsernames, hasValidatedProfiles, result?.profiles],
  )

  const missingUsernames = useMemo(
    () =>
      orderedProfiles
        .filter((profile) => !profile.exists)
        .map((profile) => profile.username),
    [orderedProfiles],
  )

  const expiredUsernames = useMemo(
    () =>
      orderedProfiles
        .filter((profile) => profile.exists && profile.expired)
        .map((profile) => profile.username),
    [orderedProfiles],
  )

  const existingUsernames = useMemo(
    () =>
      orderedProfiles
        .filter((profile) => profile.exists && !profile.expired)
        .map((profile) => profile.username),
    [orderedProfiles],
  )

  const validateProfiles = async (requestedUsernames: string[]) => {
    if (requestedUsernames.length === 0) {
      resetValidationState()
      return null
    }

    return validationMutation.mutateAsync(requestedUsernames)
  }

  return {
    existingUsernames,
    expiredUsernames,
    hasValidatedProfiles,
    isValidationPending: validationMutation.isPending,
    isValidationStale,
    missingUsernames,
    orderedProfiles,
    validateProfiles,
    validatedUsernames,
    validationError,
  }
}
