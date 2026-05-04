import { Box, Heading, SimpleGrid, Text } from "@chakra-ui/react"
import { useTranslation } from "react-i18next"

import type { ProfileSnapshotExpanded } from "@/client"
import CreatorSnapshotCard from "@/components/CreatorsSearch/CreatorSnapshotCard"

import { ResultSkeletonCard } from "./ResultSkeletonCard"
import { SearchOverviewCard } from "./SearchOverviewCard"

type ReportMutation = {
  isPending: boolean
  mutate: (username: string) => void
  variables?: string
}

export const SearchResultsSection = ({
  expiredSet,
  expiredUsernames,
  hasSearched,
  isSearchPending,
  missingUsernames,
  reportMutation,
  searchError,
  snapshots,
  submittedUsernames,
  onOpenSnapshot,
}: {
  expiredSet: ReadonlySet<string>
  expiredUsernames: string[]
  hasSearched: boolean
  isSearchPending: boolean
  missingUsernames: string[]
  reportMutation: ReportMutation
  searchError: string | null
  snapshots: ProfileSnapshotExpanded[]
  submittedUsernames: string[]
  onOpenSnapshot: (snapshot: ProfileSnapshotExpanded) => void
}) => {
  const { t } = useTranslation("creatorsSearch")

  return (
    <>
      {hasSearched && !isSearchPending ? (
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
            label={t("results.overview.found", { count: snapshots.length })}
            tone="success"
            value={String(snapshots.length)}
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

      {isSearchPending ? (
        <SimpleGrid columns={{ base: 1, xl: 2 }} gap={6}>
          <ResultSkeletonCard />
          <ResultSkeletonCard />
          <ResultSkeletonCard />
          <ResultSkeletonCard />
        </SimpleGrid>
      ) : snapshots.length > 0 ? (
        <SimpleGrid columns={{ base: 1, xl: 2 }} gap={6}>
          {snapshots.map((snapshot) => (
            <CreatorSnapshotCard
              key={
                snapshot._id || `${snapshot.profile_id}-${snapshot.scraped_at}`
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
              onOpenDetails={() => onOpenSnapshot(snapshot)}
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
            {t("results.empty.eyebrow")}
          </Text>
          <Heading mt={2} size="md">
            {t("results.empty.title")}
          </Heading>
          <Text mt={3} color="ui.secondaryText" maxW="56ch">
            {t("results.empty.description")}
          </Text>
        </Box>
      ) : null}
    </>
  )
}
