import { Box, Heading, SimpleGrid, Text } from "@chakra-ui/react"
import { useTranslation } from "react-i18next"

import type { ProfileSnapshotExpanded } from "@/client"
import CreatorSnapshotCard from "@/components/CreatorsSearch/CreatorSnapshotCard"
import { ResultSkeletonCard } from "./ResultSkeletonCard"

type ReportMutation = {
  isPending: boolean
  mutate: (username: string) => void
  variables?: string
}

export const SearchResultsSection = ({
  expiredSet,
  hasSearched,
  isSearchPending,
  reportMutation,
  searchError,
  snapshots,
  onOpenSnapshot,
}: {
  expiredSet: ReadonlySet<string>
  hasSearched: boolean
  isSearchPending: boolean
  reportMutation: ReportMutation
  searchError: string | null
  snapshots: ProfileSnapshotExpanded[]
  onOpenSnapshot: (snapshot: ProfileSnapshotExpanded) => void
}) => {
  const { t } = useTranslation("creatorsSearch")

  return (
    <Box layerStyle="dashboardCard" p={{ base: 5, md: 6, lg: 7 }} h="100%">
      <Text color="ui.mutedText" fontSize="xs" fontWeight="bold">
        {t("results.panel.eyebrow")}
      </Text>
      <Heading mt={2} fontSize="xl">
        {t("results.panel.title")}
      </Heading>
      <Text mt={2} color="ui.secondaryText" fontSize="sm">
        {hasSearched
          ? t("results.panel.descriptionActive")
          : t("results.panel.descriptionIdle")}
      </Text>

      <Box
        mt={4}
        pt={2}
        maxH={{ base: "none", xl: "960px" }}
        overflowY={{ base: "visible", xl: "auto" }}
        pr={{ base: 0, xl: 1 }}
      >
        {isSearchPending ? (
          <SimpleGrid columns={{ base: 1, xl: 2 }} gap={6}>
            <ResultSkeletonCard />
            <ResultSkeletonCard />
            <ResultSkeletonCard />
          </SimpleGrid>
        ) : snapshots.length > 0 ? (
          <SimpleGrid columns={{ base: 1, xl: 2 }} gap={6}>
            {snapshots.map((snapshot) => (
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
                onOpenDetails={() => onOpenSnapshot(snapshot)}
              />
            ))}
          </SimpleGrid>
        ) : hasSearched && !searchError ? (
          <Box
            rounded="26px"
            borderWidth="1px"
            borderColor="ui.borderSoft"
            bg="ui.surfaceSoft"
            px={5}
            py={8}
            textAlign="center"
          >
            <Text fontWeight="black">{t("results.empty.title")}</Text>
            <Text mt={2} color="ui.secondaryText">
              {t("results.empty.description")}
            </Text>
          </Box>
        ) : (
          <Box
            rounded="26px"
            borderWidth="1px"
            borderColor="ui.borderSoft"
            bg="ui.surfaceSoft"
            px={5}
            py={8}
            textAlign="center"
          >
            <Text fontWeight="black">{t("results.idle.title")}</Text>
            <Text mt={2} color="ui.secondaryText">
              {t("results.idle.description")}
            </Text>
          </Box>
        )}
      </Box>
    </Box>
  )
}
