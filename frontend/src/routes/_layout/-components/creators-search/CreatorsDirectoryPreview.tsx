import {
  Box,
  CheckboxGroup,
  Flex,
  Grid,
  Heading,
  HStack,
  Input,
  Separator,
  SimpleGrid,
  Skeleton,
  Text,
  VStack,
} from "@chakra-ui/react"
import { useMutation, useQuery } from "@tanstack/react-query"
import { useMemo, useState } from "react"
import { useTranslation } from "react-i18next"
import {
  FiCheck,
  FiChevronRight,
  FiGrid,
  FiRefreshCw,
  FiSearch,
  FiSliders,
  FiStar,
  FiX,
} from "react-icons/fi"
import CreatorSnapshotDetailDialog from "@/components/CreatorsSearch/CreatorSnapshotDetailDialog"
import { Button } from "@/components/ui/button"
import { Checkbox } from "@/components/ui/checkbox"
import {
  DialogBody,
  DialogCloseTrigger,
  DialogContent,
  DialogFooter,
  DialogHeader,
  DialogRoot,
  DialogTitle,
} from "@/components/ui/dialog"
import {
  PaginationItems,
  PaginationNextTrigger,
  PaginationPageText,
  PaginationPrevTrigger,
  PaginationRoot,
} from "@/components/ui/pagination"
import {
  getCreatorDirectoryFullProfile,
  searchCreatorsDirectory,
} from "@/features/creators-directory/api"
import {
  CREATOR_DIRECTORY_CATEGORY_OPTIONS,
  CREATOR_DIRECTORY_RANGE_PRESETS,
  CREATOR_DIRECTORY_ROLE_OPTIONS,
  CREATOR_DIRECTORY_SORT_OPTIONS,
} from "@/features/creators-directory/catalogs"
import type {
  CreatorDirectoryAppliedFilters,
  CreatorDirectoryProfile,
  CreatorDirectorySearchRequest,
} from "@/features/creators-directory/types"
import {
  buildCreatorDirectoryRequest,
  formatCompactCount,
  getDirectoryProfilePrimaryLabel,
  getDirectoryProfileRoleLabel,
  getDirectoryProfileStatus,
  isDirectoryProfileCurrent,
} from "@/features/creators-directory/utils"
import { extractApiErrorMessage } from "@/lib/api-errors"
import { enqueueCreatorsSearchScrapeJobs } from "@/routes/_layout/-components/creators-search/creators-search.api"

type FilterDialogKind = "categories" | "roles" | "range" | "sort" | null
type UpdateQueueItem = {
  id: string
  username: string
  fullName: string
}

const filterCardProps = {
  borderWidth: "1px",
  borderColor: "ui.border",
  bg: "ui.panel",
  boxShadow: "ui.card",
  rounded: "28px",
} as const

const DEFAULT_PAGE_SIZE = 20
const MAX_UPDATE_QUEUE_ITEMS = 50

export function CreatorsDirectoryPreview({
  onRequestDirectSearchFocus,
}: {
  onRequestDirectSearchFocus?: () => void
}) {
  const { t, i18n } = useTranslation("creatorsSearch")
  const [updateQueue, setUpdateQueue] = useState<UpdateQueueItem[]>([])
  const [updateQueueError, setUpdateQueueError] = useState<string | null>(null)
  const [queryInput, setQueryInput] = useState("")
  const [selectedCategories, setSelectedCategories] = useState<string[]>([])
  const [selectedRoles, setSelectedRoles] = useState<string[]>([])
  const [selectedRangePresetKey, setSelectedRangePresetKey] = useState<
    string | null
  >(null)
  const [selectedFollowerMin, setSelectedFollowerMin] = useState<string>("1")
  const [selectedFollowerMax, setSelectedFollowerMax] = useState<string>("")
  const [selectedSortBy, setSelectedSortBy] = useState<
    "username" | "follower_count"
  >("follower_count")
  const [selectedSortOrder, setSelectedSortOrder] = useState<"asc" | "desc">(
    "desc",
  )
  const [activeDialog, setActiveDialog] = useState<FilterDialogKind>(null)
  const [draftSelection, setDraftSelection] = useState<string[]>([])
  const [draftRangePresetKey, setDraftRangePresetKey] = useState<string | null>(
    null,
  )
  const [draftFollowerMin, setDraftFollowerMin] = useState<string>("1")
  const [draftFollowerMax, setDraftFollowerMax] = useState<string>("")
  const [draftSortBy, setDraftSortBy] = useState<"username" | "follower_count">(
    "follower_count",
  )
  const [draftSortOrder, setDraftSortOrder] = useState<"asc" | "desc">("desc")
  const [appliedFilters, setAppliedFilters] =
    useState<CreatorDirectoryAppliedFilters | null>(null)
  const [requestedQuery, setRequestedQuery] = useState("")
  const [page, setPage] = useState(1)
  const [selectedProfileId, setSelectedProfileId] = useState<string | null>(
    null,
  )

  const searchRequest = useMemo<CreatorDirectorySearchRequest | null>(() => {
    if (!appliedFilters) {
      return null
    }

    return buildCreatorDirectoryRequest({
      page,
      query: requestedQuery,
      filters: appliedFilters,
    })
  }, [appliedFilters, page, requestedQuery])

  const searchQuery = useQuery({
    queryKey: ["creator-directory-search", searchRequest],
    queryFn: () => {
      if (!searchRequest) {
        throw new Error("Search request is not ready.")
      }
      return searchCreatorsDirectory(searchRequest)
    },
    enabled: searchRequest !== null,
    placeholderData: (previousData) => previousData,
    retry: false,
  })

  const fullProfileQuery = useQuery({
    queryKey: ["creator-directory-full-profile", selectedProfileId],
    queryFn: () => {
      if (!selectedProfileId) {
        throw new Error("Profile detail is not ready.")
      }
      return getCreatorDirectoryFullProfile(selectedProfileId)
    },
    enabled: selectedProfileId !== null,
    retry: false,
  })

  const updateQueueMutation = useMutation({
    mutationFn: (usernames: string[]) =>
      enqueueCreatorsSearchScrapeJobs("expired", usernames),
    onMutate: () => {
      setUpdateQueueError(null)
    },
    onSuccess: ({ batchCount, createdCount, skippedCount }) => {
      if (batchCount > 0 && createdCount === 0 && skippedCount === batchCount) {
        setUpdateQueueError(t("jobs.errors.duplicateActiveJob"))
        return
      }

      setUpdateQueue([])
      onRequestDirectSearchFocus?.()
    },
    onError: (error) => {
      setUpdateQueueError(
        extractApiErrorMessage(error, t("jobs.errors.unableToCreate")),
      )
    },
  })

  const updateQueueIds = useMemo(
    () => new Set(updateQueue.map((item) => item.id)),
    [updateQueue],
  )

  const openDialog = (kind: Exclude<FilterDialogKind, null>) => {
    if (kind === "categories") {
      setDraftSelection(selectedCategories)
    }
    if (kind === "roles") {
      setDraftSelection(selectedRoles)
    }
    if (kind === "range") {
      setDraftRangePresetKey(selectedRangePresetKey)
      setDraftFollowerMin(selectedFollowerMin || "1")
      setDraftFollowerMax(selectedFollowerMax)
    }
    if (kind === "sort") {
      setDraftSortBy(selectedSortBy)
      setDraftSortOrder(selectedSortOrder)
    }
    setActiveDialog(kind)
  }

  const closeDialog = () => {
    setActiveDialog(null)
    setDraftSelection([])
    setDraftRangePresetKey(null)
    setDraftFollowerMin("1")
    setDraftFollowerMax("")
  }

  const applyDialogSelection = () => {
    if (activeDialog === "categories") {
      setSelectedCategories(draftSelection)
    }
    if (activeDialog === "roles") {
      setSelectedRoles(draftSelection)
    }
    if (activeDialog === "range") {
      const preset = CREATOR_DIRECTORY_RANGE_PRESETS.find(
        (option) => option.key === draftRangePresetKey,
      )
      if (preset) {
        setSelectedRangePresetKey(preset.key)
        setSelectedFollowerMin(String(preset.min))
        setSelectedFollowerMax(preset.max !== null ? String(preset.max) : "")
      } else {
        setSelectedRangePresetKey("manual")
        setSelectedFollowerMin(draftFollowerMin.trim() || "1")
        setSelectedFollowerMax(draftFollowerMax.trim())
      }
    }
    if (activeDialog === "sort") {
      setSelectedSortBy(draftSortBy)
      setSelectedSortOrder(draftSortOrder)
    }
    setPage(1)
    closeDialog()
  }

  const handleSearch = () => {
    setAppliedFilters({
      ai_categories: selectedCategories,
      ai_roles: selectedRoles,
      follower_count_min: Number(selectedFollowerMin || "1"),
      follower_count_max: selectedFollowerMax
        ? Number(selectedFollowerMax)
        : undefined,
      sort_by: selectedSortBy,
      sort_order: selectedSortOrder,
      page_size: DEFAULT_PAGE_SIZE,
    })
    setRequestedQuery(queryInput)
    setPage(1)
  }

  const handleReset = () => {
    setQueryInput("")
    setSelectedCategories([])
    setSelectedRoles([])
    setSelectedRangePresetKey(null)
    setSelectedFollowerMin("1")
    setSelectedFollowerMax("")
    setSelectedSortBy("follower_count")
    setSelectedSortOrder("desc")
    setAppliedFilters(null)
    setRequestedQuery("")
    setPage(1)
    setSelectedProfileId(null)
    closeDialog()
  }

  const addProfileToUpdateQueue = (profile: CreatorDirectoryProfile) => {
    const profileId = profile._id ?? profile.username
    if (updateQueueIds.has(profileId)) {
      return
    }

    if (updateQueue.length >= MAX_UPDATE_QUEUE_ITEMS) {
      setUpdateQueueError(
        t("directoryPreview.updateQueue.limitError", {
          max: MAX_UPDATE_QUEUE_ITEMS,
        }),
      )
      return
    }

    setUpdateQueueError(null)
    setUpdateQueue((current) => [
      ...current,
      {
        id: profileId,
        username: profile.username,
        fullName: profile.full_name || t("card.fallbackName"),
      },
    ])
  }

  const removeProfileFromUpdateQueue = (profileId: string) => {
    setUpdateQueue((current) => current.filter((item) => item.id !== profileId))
    setUpdateQueueError(null)
  }

  const handleUpdateQueueSubmit = () => {
    const usernames = [
      ...new Set(updateQueue.map((item) => item.username)),
    ].slice(0, MAX_UPDATE_QUEUE_ITEMS)
    if (usernames.length === 0) {
      return
    }

    updateQueueMutation.mutate(usernames)
  }

  const activeOptions =
    activeDialog === "categories"
      ? CREATOR_DIRECTORY_CATEGORY_OPTIONS
      : CREATOR_DIRECTORY_ROLE_OPTIONS
  const activeTitle =
    activeDialog === "categories"
      ? t("directoryPreview.filters.categoryDialog.title")
      : activeDialog === "roles"
        ? t("directoryPreview.filters.roleDialog.title")
        : activeDialog === "range"
          ? t("directoryPreview.filters.rangeDialog.title")
          : t("directoryPreview.filters.sortDialog.title")
  const activeDescription =
    activeDialog === "categories"
      ? t("directoryPreview.filters.categoryDialog.description")
      : activeDialog === "roles"
        ? t("directoryPreview.filters.roleDialog.description")
        : activeDialog === "range"
          ? t("directoryPreview.filters.rangeDialog.description")
          : t("directoryPreview.filters.sortDialog.description")

  const selectedRangePreset = CREATOR_DIRECTORY_RANGE_PRESETS.find(
    (option) => option.key === selectedRangePresetKey,
  )
  const selectedSortByLabel = t(
    CREATOR_DIRECTORY_SORT_OPTIONS.find(
      (option) => option.value === selectedSortBy,
    )?.labelKey ?? "directoryPreview.filters.sortDialog.options.followerCount",
  )

  const resultState = (() => {
    if (!appliedFilters) {
      return "idle" as const
    }
    if (searchQuery.isLoading) {
      return "loading" as const
    }
    if (searchQuery.error) {
      return "error" as const
    }
    if ((searchQuery.data?.profiles.length ?? 0) === 0) {
      return "empty" as const
    }
    return "success" as const
  })()

  return (
    <Box>
      {updateQueue.length > 0 ? (
        <Box
          {...filterCardProps}
          mb={6}
          p={{ base: 5, md: 6 }}
          data-testid="directory-update-queue-card"
        >
          <Flex
            justify="space-between"
            align={{ base: "flex-start", md: "center" }}
            direction={{ base: "column", md: "row" }}
            gap={3}
          >
            <Box>
              <Text color="ui.mutedText" fontSize="xs" fontWeight="bold">
                {t("directoryPreview.updateQueue.eyebrow")}
              </Text>
              <Heading mt={2} fontSize="xl">
                {t("directoryPreview.updateQueue.title")}
              </Heading>
              <Text mt={2} color="ui.secondaryText" fontSize="sm">
                {t("directoryPreview.updateQueue.description")}
              </Text>
            </Box>

            <HStack
              gap={2}
              px={3}
              py={2}
              rounded="full"
              borderWidth="1px"
              borderColor="ui.borderSoft"
              bg="ui.surfaceSoft"
              color="ui.secondaryText"
              fontSize="sm"
              fontWeight="medium"
            >
              <FiRefreshCw />
              <Text>
                {t("directoryPreview.updateQueue.count", {
                  count: updateQueue.length,
                  max: MAX_UPDATE_QUEUE_ITEMS,
                })}
              </Text>
            </HStack>
          </Flex>

          <HStack
            mt={5}
            align="stretch"
            gap={3}
            wrap="wrap"
            maxH={{ base: "240px", md: "280px" }}
            overflowY="auto"
            pr={1}
          >
            {updateQueue.map((item) => (
              <HStack
                key={item.id}
                align="center"
                gap={2}
                rounded="full"
                borderWidth="1px"
                borderColor="ui.borderSoft"
                bg="ui.surfaceSoft"
                px={3}
                py={1.5}
                minH="0"
                maxW="full"
              >
                <Text
                  fontSize="sm"
                  fontWeight="bold"
                  color="ui.brandText"
                  lineClamp={1}
                >
                  @{item.username}
                </Text>

                <Button
                  size="2xs"
                  variant="ghost"
                  minW="6"
                  h="6"
                  px={0}
                  color="ui.brandText"
                  aria-label={t("directoryPreview.updateQueue.removeAction")}
                  title={t("directoryPreview.updateQueue.removeAction")}
                  onClick={() => removeProfileFromUpdateQueue(item.id)}
                >
                  <FiX />
                </Button>
              </HStack>
            ))}
          </HStack>

          <Button
            mt={5}
            size="sm"
            onClick={handleUpdateQueueSubmit}
            disabled={updateQueueMutation.isPending}
            loading={updateQueueMutation.isPending}
          >
            <FiRefreshCw />
            {t("directoryPreview.updateQueue.submitAction")}
          </Button>

          {updateQueueError ? (
            <Text
              mt={3}
              color="ui.dangerText"
              fontSize="sm"
              fontWeight="medium"
            >
              {updateQueueError}
            </Text>
          ) : null}
        </Box>
      ) : null}

      <Grid
        templateColumns={{ base: "1fr", xl: "320px minmax(0, 1fr)" }}
        gap={6}
      >
        <Box
          {...filterCardProps}
          p={{ base: 5, md: 6 }}
          data-testid="directory-filters-card"
        >
          <HStack justify="space-between" align="center" mb={4}>
            <Box>
              <Text color="ui.mutedText" fontSize="xs" fontWeight="bold">
                {t("directoryPreview.filters.eyebrow")}
              </Text>
              <Heading mt={2} fontSize="xl">
                {t("directoryPreview.filters.title")}
              </Heading>
            </Box>
            <Flex
              boxSize="10"
              rounded="full"
              align="center"
              justify="center"
              bg="ui.surfaceSoft"
              color="ui.brandText"
            >
              <FiSliders />
            </Flex>
          </HStack>

          <Button
            width="full"
            size="sm"
            onClick={handleSearch}
            loading={searchQuery.isFetching}
          >
            <FiSearch />
            {t("directoryPreview.filters.searchAction")}
          </Button>
          <Button
            mt={3}
            width="full"
            size="sm"
            variant="outline"
            onClick={handleReset}
          >
            {t("directoryPreview.filters.resetAction")}
          </Button>

          <Box mt={5}>
            <HStack justify="space-between" align="center" mb={3}>
              <Text fontSize="sm" fontWeight="bold" color="ui.text">
                {t("directoryPreview.filters.categories")}
              </Text>
              <Button
                size="sm"
                variant="outline"
                onClick={() => openDialog("categories")}
              >
                {t("directoryPreview.filters.categoryDialog.trigger")}
                <FiChevronRight />
              </Button>
            </HStack>
            {selectedCategories.length > 0 ? (
              <HStack gap={2} wrap="wrap">
                {selectedCategories.map((item) => (
                  <Box
                    key={item}
                    px={3}
                    py={2}
                    rounded="full"
                    borderWidth="1px"
                    borderColor="ui.brandBorderSoft"
                    bg="ui.brandSoft"
                    color="ui.brandText"
                    fontSize="sm"
                    fontWeight="bold"
                  >
                    {item}
                  </Box>
                ))}
              </HStack>
            ) : (
              <Text fontSize="sm" color="ui.secondaryText">
                {t("directoryPreview.filters.categoryDialog.empty")}
              </Text>
            )}
          </Box>

          <Box mt={5}>
            <HStack justify="space-between" align="center" mb={3}>
              <Text fontSize="sm" fontWeight="bold" color="ui.text">
                {t("directoryPreview.filters.roles")}
              </Text>
              <Button
                size="sm"
                variant="outline"
                onClick={() => openDialog("roles")}
              >
                {t("directoryPreview.filters.roleDialog.trigger")}
                <FiChevronRight />
              </Button>
            </HStack>
            {selectedRoles.length > 0 ? (
              <HStack gap={2} wrap="wrap">
                {selectedRoles.map((item) => (
                  <Box
                    key={item}
                    px={3}
                    py={2}
                    rounded="full"
                    borderWidth="1px"
                    borderColor="ui.infoText"
                    bg="ui.infoSoft"
                    color="ui.infoText"
                    fontSize="sm"
                    fontWeight="bold"
                  >
                    {item}
                  </Box>
                ))}
              </HStack>
            ) : (
              <Text fontSize="sm" color="ui.secondaryText">
                {t("directoryPreview.filters.roleDialog.empty")}
              </Text>
            )}
          </Box>

          <Separator my={5} borderColor="ui.borderSoft" />

          <Box mt={5}>
            <HStack justify="space-between" align="center" mb={3}>
              <Text fontSize="sm" fontWeight="bold" color="ui.text">
                {t("directoryPreview.filters.range")}
              </Text>
              <Button
                size="sm"
                variant="outline"
                onClick={() => openDialog("range")}
              >
                {t("directoryPreview.filters.rangeDialog.trigger")}
                <FiChevronRight />
              </Button>
            </HStack>
            <HStack gap={2} wrap="wrap">
              {selectedRangePreset ? (
                <Box
                  px={3}
                  py={2}
                  rounded="full"
                  borderWidth="1px"
                  borderColor="ui.brandBorderSoft"
                  bg="ui.brandSoft"
                  color="ui.brandText"
                  fontSize="sm"
                  fontWeight="bold"
                >
                  {selectedRangePreset.label}
                </Box>
              ) : null}
              <Box
                px={3}
                py={2}
                rounded="full"
                borderWidth="1px"
                borderColor="ui.borderSoft"
                bg="ui.surfaceSoft"
                color="ui.text"
                fontSize="sm"
                fontWeight="bold"
              >
                {t("directoryPreview.filters.rangeDialog.minChip", {
                  value: selectedFollowerMin,
                })}
              </Box>
              {selectedFollowerMax ? (
                <Box
                  px={3}
                  py={2}
                  rounded="full"
                  borderWidth="1px"
                  borderColor="ui.borderSoft"
                  bg="ui.surfaceSoft"
                  color="ui.text"
                  fontSize="sm"
                  fontWeight="bold"
                >
                  {t("directoryPreview.filters.rangeDialog.maxChip", {
                    value: selectedFollowerMax,
                  })}
                </Box>
              ) : null}
            </HStack>
          </Box>

          <Box mt={5}>
            <HStack justify="space-between" align="center" mb={3}>
              <Text fontSize="sm" fontWeight="bold" color="ui.text">
                {t("directoryPreview.filters.sort")}
              </Text>
              <Button
                size="sm"
                variant="outline"
                onClick={() => openDialog("sort")}
              >
                {t("directoryPreview.filters.sortDialog.trigger")}
                <FiChevronRight />
              </Button>
            </HStack>
            <HStack gap={2} wrap="wrap" justify="center">
              <Box
                px={3}
                py={2}
                rounded="full"
                borderWidth="1px"
                borderColor="ui.infoText"
                bg="ui.infoSoft"
                color="ui.infoText"
                fontSize="sm"
                fontWeight="bold"
              >
                {selectedSortByLabel}
              </Box>
              <Box
                px={3}
                py={2}
                rounded="full"
                borderWidth="1px"
                borderColor="ui.borderSoft"
                bg="ui.surfaceSoft"
                color="ui.text"
                fontSize="sm"
                fontWeight="bold"
              >
                {selectedSortOrder.toUpperCase()}
              </Box>
            </HStack>
          </Box>

          <Separator my={5} borderColor="ui.borderSoft" />

          <Box mt={5}>
            <HStack justify="space-between" align="center" mb={2}>
              <Text fontSize="sm" fontWeight="bold" color="ui.text">
                {t("directoryPreview.filters.searchLabel")}
              </Text>
              <Text color="ui.mutedText" fontSize="xs" fontWeight="bold">
                {t("directoryPreview.filters.optional")}
              </Text>
            </HStack>

            <Input
              value={queryInput}
              onChange={(event) => setQueryInput(event.target.value)}
              placeholder={t("directoryPreview.filters.searchPlaceholder")}
              rounded="22px"
              borderColor="ui.borderSoft"
              bg="ui.surfaceSoft"
              px={4}
              py={3.5}
            />
            {queryInput.trim().length > 0 && queryInput.trim().length < 3 ? (
              <Text mt={2} color="ui.mutedText" fontSize="xs">
                {t("directoryPreview.filters.searchHint")}
              </Text>
            ) : null}
          </Box>
        </Box>

        <Box {...filterCardProps} p={{ base: 5, md: 6 }}>
          <Flex
            justify="space-between"
            align={{ base: "flex-start", md: "center" }}
            direction={{ base: "column", md: "row" }}
            gap={3}
          >
            <Box>
              <Text color="ui.mutedText" fontSize="xs" fontWeight="bold">
                {t("directoryPreview.results.eyebrow")}
              </Text>
              <Heading mt={2} fontSize="xl">
                {t("directoryPreview.results.title")}
              </Heading>
            </Box>

            {resultState !== "idle" && searchQuery.data ? (
              <HStack
                gap={2}
                px={3}
                py={2}
                rounded="full"
                borderWidth="1px"
                borderColor="ui.borderSoft"
                bg="ui.surfaceSoft"
                color="ui.secondaryText"
                fontSize="sm"
                fontWeight="medium"
              >
                <FiStar />
                <Text>
                  {t("directoryPreview.results.summary", {
                    total: searchQuery.data.pagination.total,
                  })}
                </Text>
              </HStack>
            ) : null}
          </Flex>

          {resultState === "idle" ? (
            <Box
              mt={5}
              rounded="26px"
              borderWidth="1px"
              borderColor="ui.borderSoft"
              bg="ui.surfaceSoft"
              px={5}
              py={8}
              textAlign="center"
            >
              <Text fontWeight="black">
                {t("directoryPreview.results.idleTitle")}
              </Text>
              <Text mt={2} color="ui.secondaryText">
                {t("directoryPreview.results.idleDescription")}
              </Text>
            </Box>
          ) : null}

          {resultState === "loading" ? (
            <SimpleGrid mt={5} columns={{ base: 1, lg: 2, "2xl": 3 }} gap={4}>
              {Array.from({ length: 3 }).map((_, index) => (
                <Skeleton key={index} h="260px" rounded="3xl" />
              ))}
            </SimpleGrid>
          ) : null}

          {resultState === "error" ? (
            <Box
              mt={5}
              rounded="26px"
              borderWidth="1px"
              borderColor="ui.danger"
              bg="ui.dangerSoft"
              px={5}
              py={6}
            >
              <Text color="ui.dangerText" fontWeight="black">
                {t("directoryPreview.results.errorTitle")}
              </Text>
              <Text mt={2} color="ui.secondaryText">
                {extractApiErrorMessage(
                  searchQuery.error,
                  t("directoryPreview.results.errorFallback"),
                )}
              </Text>
            </Box>
          ) : null}

          {resultState === "empty" ? (
            <Box
              mt={5}
              rounded="26px"
              borderWidth="1px"
              borderColor="ui.borderSoft"
              bg="ui.surfaceSoft"
              px={5}
              py={8}
              textAlign="center"
            >
              <Text fontWeight="black">
                {t("directoryPreview.results.emptyTitle")}
              </Text>
              <Text mt={2} color="ui.secondaryText">
                {t("directoryPreview.results.emptyDescription")}
              </Text>
            </Box>
          ) : null}

          {resultState === "success" && searchQuery.data ? (
            <>
              <SimpleGrid mt={5} columns={{ base: 1, lg: 2, "2xl": 3 }} gap={4}>
                {searchQuery.data.profiles.map((profile) => (
                  <Box
                    key={profile._id ?? profile.username}
                    rounded="26px"
                    borderWidth="1px"
                    borderColor="ui.border"
                    bg="ui.panel"
                    boxShadow="ui.card"
                    px={4.5}
                    py={4.5}
                    opacity={searchQuery.isFetching ? 0.7 : 1}
                  >
                    {(() => {
                      const isCurrent = isDirectoryProfileCurrent(profile)
                      const statusLabel = getDirectoryProfileStatus({
                        profile,
                        t,
                      })
                      const queueId = profile._id ?? profile.username
                      const isQueuedForUpdate = updateQueueIds.has(queueId)

                      return (
                        <>
                          <Flex
                            justify="space-between"
                            align="flex-start"
                            gap={3}
                          >
                            <Box minW={0}>
                              <Text
                                fontSize="lg"
                                fontWeight="black"
                                lineClamp={1}
                              >
                                {profile.full_name || t("card.fallbackName")}
                              </Text>
                              <Text
                                mt={1}
                                color="ui.secondaryText"
                                lineClamp={1}
                              >
                                @{profile.username}
                              </Text>
                            </Box>
                            <Box
                              px={2.5}
                              py={1.5}
                              rounded="full"
                              bg={
                                isCurrent ? "ui.successSoft" : "ui.warningSoft"
                              }
                              color={
                                isCurrent ? "ui.successText" : "ui.warningText"
                              }
                              fontSize="xs"
                              fontWeight="bold"
                              whiteSpace="nowrap"
                            >
                              {statusLabel}
                            </Box>
                          </Flex>

                          <Text mt={4} color="ui.text" fontWeight="medium">
                            {getDirectoryProfilePrimaryLabel(profile, t)}
                          </Text>
                          <Text mt={1.5} color="ui.secondaryText" fontSize="sm">
                            {getDirectoryProfileRoleLabel(profile, t)}
                          </Text>

                          <Grid
                            mt={5}
                            templateColumns="repeat(2, minmax(0, 1fr))"
                            gap={3}
                          >
                            <Box
                              rounded="18px"
                              borderWidth="1px"
                              borderColor="ui.borderSoft"
                              bg="ui.surfaceSoft"
                              px={3}
                              py={3}
                            >
                              <Text
                                fontSize="xs"
                                color="ui.mutedText"
                                fontWeight="bold"
                              >
                                {t("directoryPreview.results.followers")}
                              </Text>
                              <Text mt={1.5} fontWeight="black" fontSize="lg">
                                {formatCompactCount(
                                  profile.follower_count,
                                  i18n.language,
                                )}
                              </Text>
                            </Box>
                            <Box
                              rounded="18px"
                              borderWidth="1px"
                              borderColor="ui.borderSoft"
                              bg="ui.surfaceSoft"
                              px={3}
                              py={3}
                            >
                              <Text
                                fontSize="xs"
                                color="ui.mutedText"
                                fontWeight="bold"
                              >
                                {t("directoryPreview.results.media")}
                              </Text>
                              <Text mt={1.5} fontWeight="black" fontSize="lg">
                                {profile.media_count}
                              </Text>
                            </Box>
                          </Grid>

                          <Button
                            mt={5}
                            size="sm"
                            variant="outline"
                            width="full"
                            disabled={!profile._id}
                            loading={
                              selectedProfileId === profile._id &&
                              fullProfileQuery.isLoading
                            }
                            onClick={() => {
                              if (profile._id) {
                                setSelectedProfileId(profile._id)
                              }
                            }}
                          >
                            <FiGrid />
                            {t("directoryPreview.results.viewProfile")}
                          </Button>
                          {!isCurrent ? (
                            <Button
                              mt={3}
                              size="sm"
                              variant="subtle"
                              width="full"
                              disabled={
                                isQueuedForUpdate ||
                                updateQueue.length >= MAX_UPDATE_QUEUE_ITEMS
                              }
                              onClick={() => addProfileToUpdateQueue(profile)}
                            >
                              {isQueuedForUpdate ? (
                                <FiCheck />
                              ) : (
                                <FiRefreshCw />
                              )}
                              {isQueuedForUpdate
                                ? t("directoryPreview.updateQueue.addedAction")
                                : t("directoryPreview.updateQueue.addAction")}
                            </Button>
                          ) : null}
                        </>
                      )
                    })()}
                  </Box>
                ))}
              </SimpleGrid>

              {searchQuery.data.pagination.total_pages > 1 ? (
                <Flex
                  mt={5}
                  justify="space-between"
                  align={{ base: "flex-start", md: "center" }}
                  gap={3}
                  direction={{ base: "column", md: "row" }}
                >
                  <PaginationRoot
                    count={searchQuery.data.pagination.total}
                    page={searchQuery.data.pagination.page}
                    pageSize={searchQuery.data.pagination.page_size}
                    onPageChange={({ page: nextPage }) => setPage(nextPage)}
                  >
                    <Flex
                      justify="space-between"
                      align={{ base: "flex-start", md: "center" }}
                      gap={3}
                      direction={{ base: "column", md: "row" }}
                      width="full"
                    >
                      <HStack>
                        <PaginationPrevTrigger />
                        <PaginationItems />
                        <PaginationNextTrigger />
                      </HStack>
                      <PaginationPageText
                        format="compact"
                        color="ui.secondaryText"
                      />
                    </Flex>
                  </PaginationRoot>
                </Flex>
              ) : null}
            </>
          ) : null}
        </Box>
      </Grid>

      <CreatorSnapshotDetailDialog
        open={selectedProfileId !== null}
        loading={fullProfileQuery.isLoading}
        errorMessage={
          fullProfileQuery.error
            ? extractApiErrorMessage(
                fullProfileQuery.error,
                t("detail.errorTitle"),
              )
            : null
        }
        snapshot={fullProfileQuery.data ?? null}
        onOpenChange={(open) => {
          if (!open) {
            setSelectedProfileId(null)
          }
        }}
      />

      <DialogRoot
        open={activeDialog !== null}
        placement="center"
        onOpenChange={({ open }) => {
          if (!open) {
            closeDialog()
          }
        }}
      >
        <DialogContent
          maxW="xl"
          rounded="3xl"
          borderWidth="1px"
          borderColor="ui.border"
        >
          <DialogCloseTrigger />
          <DialogHeader px={6} pt={6}>
            <DialogTitle
              fontSize={{ base: "xl", md: "2xl" }}
              fontWeight="black"
              letterSpacing="-0.02em"
            >
              {activeTitle}
            </DialogTitle>
            <Text mt={2} color="ui.secondaryText">
              {activeDescription}
            </Text>
          </DialogHeader>
          <DialogBody px={6} pb={6}>
            {activeDialog === "categories" || activeDialog === "roles" ? (
              <CheckboxGroup
                value={draftSelection}
                onValueChange={(value) => setDraftSelection([...value])}
              >
                <Box
                  mt={2}
                  maxH="420px"
                  overflowY="auto"
                  rounded="24px"
                  borderWidth="1px"
                  borderColor="ui.borderSoft"
                  bg="ui.surfaceSoft"
                  p={4}
                >
                  <VStack align="stretch" gap={3}>
                    {activeOptions.map((option) => (
                      <Checkbox key={option} value={option}>
                        {option}
                      </Checkbox>
                    ))}
                  </VStack>
                </Box>
              </CheckboxGroup>
            ) : null}

            {activeDialog === "range" ? (
              <VStack align="stretch" gap={5} mt={2}>
                <Box
                  rounded="24px"
                  borderWidth="1px"
                  borderColor="ui.borderSoft"
                  bg="ui.surfaceSoft"
                  p={4}
                >
                  <Text fontSize="sm" fontWeight="bold" color="ui.text" mb={3}>
                    {t("directoryPreview.filters.rangeDialog.presetsLabel")}
                  </Text>
                  <VStack align="stretch" gap={3}>
                    {CREATOR_DIRECTORY_RANGE_PRESETS.map((option) => (
                      <Button
                        key={option.key}
                        variant={
                          draftRangePresetKey === option.key
                            ? "solid"
                            : "outline"
                        }
                        justifyContent="space-between"
                        onClick={() => {
                          setDraftRangePresetKey(option.key)
                          setDraftFollowerMin(String(option.min))
                          setDraftFollowerMax(
                            option.max !== null ? String(option.max) : "",
                          )
                        }}
                      >
                        {option.label}
                      </Button>
                    ))}
                  </VStack>
                </Box>

                <Box
                  rounded="24px"
                  borderWidth="1px"
                  borderColor="ui.borderSoft"
                  bg="ui.surfaceSoft"
                  p={4}
                >
                  <Text fontSize="sm" fontWeight="bold" color="ui.text" mb={3}>
                    {t("directoryPreview.filters.rangeDialog.manualLabel")}
                  </Text>
                  <Text fontSize="sm" color="ui.secondaryText" mb={4}>
                    {t(
                      "directoryPreview.filters.rangeDialog.manualDescription",
                    )}
                  </Text>
                  <SimpleGrid columns={{ base: 1, md: 2 }} gap={3}>
                    <Box>
                      <Text
                        fontSize="xs"
                        color="ui.mutedText"
                        fontWeight="bold"
                        mb={2}
                      >
                        {t("directoryPreview.filters.rangeDialog.minLabel")}
                      </Text>
                      <Input
                        type="number"
                        min={1}
                        value={draftFollowerMin}
                        onChange={(event) => {
                          setDraftRangePresetKey("manual")
                          setDraftFollowerMin(event.target.value)
                        }}
                      />
                    </Box>
                    <Box>
                      <Text
                        fontSize="xs"
                        color="ui.mutedText"
                        fontWeight="bold"
                        mb={2}
                      >
                        {t("directoryPreview.filters.rangeDialog.maxLabel")}
                      </Text>
                      <Input
                        type="number"
                        min={1}
                        value={draftFollowerMax}
                        onChange={(event) => {
                          setDraftRangePresetKey("manual")
                          setDraftFollowerMax(event.target.value)
                        }}
                      />
                    </Box>
                  </SimpleGrid>
                </Box>
              </VStack>
            ) : null}

            {activeDialog === "sort" ? (
              <VStack align="stretch" gap={5} mt={2}>
                <Box
                  rounded="24px"
                  borderWidth="1px"
                  borderColor="ui.borderSoft"
                  bg="ui.surfaceSoft"
                  p={4}
                >
                  <Text fontSize="sm" fontWeight="bold" color="ui.text" mb={3}>
                    {t("directoryPreview.filters.sortDialog.sortByLabel")}
                  </Text>
                  <VStack align="stretch" gap={3}>
                    {CREATOR_DIRECTORY_SORT_OPTIONS.map((option) => (
                      <Button
                        key={option.value}
                        variant={
                          draftSortBy === option.value ? "solid" : "outline"
                        }
                        justifyContent="space-between"
                        onClick={() => setDraftSortBy(option.value)}
                      >
                        {t(option.labelKey)}
                      </Button>
                    ))}
                  </VStack>
                </Box>

                <Box
                  rounded="24px"
                  borderWidth="1px"
                  borderColor="ui.borderSoft"
                  bg="ui.surfaceSoft"
                  p={4}
                >
                  <Text fontSize="sm" fontWeight="bold" color="ui.text" mb={3}>
                    {t("directoryPreview.filters.sortDialog.directionLabel")}
                  </Text>
                  <HStack gap={3}>
                    {(["asc", "desc"] as const).map((direction) => (
                      <Button
                        key={direction}
                        variant={
                          draftSortOrder === direction ? "solid" : "outline"
                        }
                        onClick={() => setDraftSortOrder(direction)}
                      >
                        {direction.toUpperCase()}
                      </Button>
                    ))}
                  </HStack>
                </Box>
              </VStack>
            ) : null}
          </DialogBody>
          <DialogFooter gap={3} px={6} pb={6}>
            <Button variant="outline" onClick={closeDialog}>
              {t("directoryPreview.filters.dialog.cancel")}
            </Button>
            <Button onClick={applyDialogSelection}>
              {t("directoryPreview.filters.dialog.add")}
            </Button>
          </DialogFooter>
        </DialogContent>
      </DialogRoot>
    </Box>
  )
}

export default CreatorsDirectoryPreview
