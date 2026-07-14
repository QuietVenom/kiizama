import { Box, Flex, Grid, Icon, Skeleton, Tabs, Text } from "@chakra-ui/react"
import { useQuery } from "@tanstack/react-query"
import { lazy, Suspense, useEffect, useState } from "react"
import { useTranslation } from "react-i18next"
import { FiGrid, FiLock, FiSearch } from "react-icons/fi"

import DashboardTopbar from "@/components/Dashboard/DashboardTopbar"
import { billingSummaryQueryOptions } from "@/features/billing/api"
import { hasActiveBillingAccess } from "@/features/billing/presentation"
import { sanitizeInstagramUsernames } from "@/lib/instagram-usernames"
import { CurrentJobDetailDialog } from "./CurrentJobDetailDialog"
import { CurrentJobsDialog } from "./CurrentJobsDialog"
import { CurrentJobsSummary } from "./CurrentJobsSummary"
import { DirectoryPaywallPanel } from "./DirectoryPaywallPanel"
import { SearchHeader } from "./SearchHeader"
import { SearchHistoryDialog } from "./SearchHistoryDialog"
import { useCreatorsSearchHistory } from "./useCreatorsSearchHistory"
import { useCreatorsSearchJobs } from "./useCreatorsSearchJobs"

const loadDirectCreatorsSearchTab = () => import("./DirectCreatorsSearchTab")
const loadCreatorsDirectoryPreview = () => import("./CreatorsDirectoryPreview")

const DirectCreatorsSearchTab = lazy(loadDirectCreatorsSearchTab)
const CreatorsDirectoryPreview = lazy(loadCreatorsDirectoryPreview)

const CreatorsSearchTabFallback = ({
  showResults = true,
}: {
  showResults?: boolean
}) => (
  <Box>
    <Grid
      templateColumns={{
        base: "1fr",
        "2xl": "minmax(0, 3fr) minmax(320px, 1fr)",
      }}
      gap={6}
      mb={{ base: 7, lg: 8 }}
    >
      <Box
        rounded="30px"
        borderWidth="1px"
        borderColor="ui.border"
        bg="ui.panel"
        boxShadow="ui.panel"
        px={{ base: 5, md: 6 }}
        py={{ base: 5, md: 6 }}
      >
        <Skeleton h="4" w="28" rounded="full" />
        <Skeleton mt={4} h="9" w="64" rounded="xl" />
        <Skeleton mt={5} h="14" rounded="2xl" />
        <Skeleton mt={4} h="12" rounded="2xl" />
      </Box>

      <Box
        rounded="30px"
        borderWidth="1px"
        borderColor="ui.border"
        bg="ui.panel"
        boxShadow="ui.panel"
        px={{ base: 5, md: 6 }}
        py={{ base: 5, md: 6 }}
      >
        <Skeleton h="4" w="24" rounded="full" />
        <Skeleton mt={4} h="8" w="44" rounded="xl" />
        <Skeleton mt={5} h="24" rounded="2xl" />
        <Skeleton mt={4} h="24" rounded="2xl" />
      </Box>
    </Grid>

    {showResults ? (
      <Grid
        templateColumns={{ base: "1fr", lg: "repeat(2, minmax(0, 1fr))" }}
        gap={6}
      >
        <Skeleton h="220px" rounded="3xl" />
        <Skeleton h="220px" rounded="3xl" />
      </Grid>
    ) : (
      <Skeleton h="520px" rounded="3xl" />
    )}
  </Box>
)

export function CreatorsSearchPage() {
  const { t } = useTranslation("creatorsSearch")
  const [activeTab, setActiveTab] = useState<
    "direct-search" | "directory-preview"
  >("direct-search")
  const [usernames, setUsernames] = useState<string[]>([])
  const [isHistoryOpen, setIsHistoryOpen] = useState(false)
  const [isJobsDialogOpen, setIsJobsDialogOpen] = useState(false)
  const { data: billing, isPending: isBillingPending } = useQuery(
    billingSummaryQueryOptions,
  )
  const isDirectoryLocked =
    !isBillingPending && !hasActiveBillingAccess(billing)

  const { persistSearchHistoryEntry, viewAllQuery } = useCreatorsSearchHistory({
    isViewAllOpen: isHistoryOpen,
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
  } = useCreatorsSearchJobs({ persistSearchHistoryEntry })

  useEffect(() => {
    void loadDirectCreatorsSearchTab()
    void loadCreatorsDirectoryPreview()
  }, [])

  const handleSelectJob = (jobId: string) => {
    setIsJobsDialogOpen(false)
    selectCurrentJob(jobId)
  }

  const handleReuseReadyUsernames = (readyUsernames: string[]) => {
    setUsernames(sanitizeInstagramUsernames(readyUsernames))
    clearSelectedCurrentJob()
    setIsHistoryOpen(false)
    setActiveTab("direct-search")
  }

  return (
    <Box minH="100vh" bg="ui.page">
      <DashboardTopbar />

      <Box px={{ base: 4, md: 7, lg: 10 }} py={{ base: 7, lg: 9 }}>
        <Tabs.Root
          value={activeTab}
          onValueChange={({ value }) =>
            setActiveTab(value as "direct-search" | "directory-preview")
          }
          variant="plain"
        >
          <SearchHeader
            rightSlot={
              <CurrentJobsSummary
                currentJobs={currentJobs}
                onSelectJob={handleSelectJob}
                onViewAll={() => setIsJobsDialogOpen(true)}
              />
            }
          >
            <Box
              mt={{ base: 5, lg: 6 }}
              p="1.5"
              rounded="full"
              borderWidth="1px"
              borderColor="ui.border"
              bg="ui.panel"
              boxShadow="ui.card"
              maxW="fit-content"
            >
              <Tabs.List
                gap="1.5"
                rounded="full"
                bg="ui.surfaceSoft"
                p="1.5"
                borderWidth="1px"
                borderColor="ui.borderSoft"
              >
                <Tabs.Trigger
                  value="direct-search"
                  onMouseEnter={() => void loadDirectCreatorsSearchTab()}
                  onFocus={() => void loadDirectCreatorsSearchTab()}
                  rounded="full"
                  minH={{ base: "64px", md: "72px" }}
                  px={{ base: 4, md: 5 }}
                  py={{ base: 3.5, md: 4 }}
                  color="ui.secondaryText"
                  transition="all 180ms ease"
                  _selected={{
                    bg: "ui.panel",
                    color: "ui.text",
                    boxShadow: "ui.card",
                  }}
                >
                  <Flex align="center" gap={3} py="0.5">
                    <Flex
                      boxSize="9"
                      rounded="full"
                      align="center"
                      justify="center"
                      bg="ui.brandSoft"
                      color="ui.brandText"
                    >
                      <Icon as={FiSearch} boxSize={4} />
                    </Flex>
                    <Box textAlign="left" py="0.5">
                      <Text fontWeight="black" lineHeight="1.15">
                        {t("tabs.direct.title")}
                      </Text>
                      <Text
                        display={{ base: "none", md: "block" }}
                        mt="1"
                        fontSize="xs"
                        lineHeight="1.35"
                        color="ui.mutedText"
                      >
                        {t("tabs.direct.description")}
                      </Text>
                    </Box>
                  </Flex>
                </Tabs.Trigger>

                <Tabs.Trigger
                  value="directory-preview"
                  onMouseEnter={() => void loadCreatorsDirectoryPreview()}
                  onFocus={() => void loadCreatorsDirectoryPreview()}
                  rounded="full"
                  minH={{ base: "64px", md: "72px" }}
                  px={{ base: 4, md: 5 }}
                  py={{ base: 3.5, md: 4 }}
                  color="ui.secondaryText"
                  transition="all 180ms ease"
                  _selected={{
                    bg: "ui.panel",
                    color: "ui.text",
                    boxShadow: "ui.card",
                  }}
                >
                  <Flex align="center" gap={3} py="0.5">
                    <Flex
                      boxSize="9"
                      rounded="full"
                      align="center"
                      justify="center"
                      bg={isDirectoryLocked ? "ui.warningSoft" : "ui.infoSoft"}
                      color={
                        isDirectoryLocked ? "ui.warningText" : "ui.infoText"
                      }
                      aria-label={
                        isDirectoryLocked
                          ? t("directoryPaywall.lockedIndicator")
                          : undefined
                      }
                    >
                      <Icon
                        as={isDirectoryLocked ? FiLock : FiGrid}
                        boxSize={4}
                      />
                    </Flex>
                    <Box textAlign="left" py="0.5">
                      <Text fontWeight="black" lineHeight="1.15">
                        {t("tabs.directory.title")}
                      </Text>
                      <Text
                        display={{ base: "none", md: "block" }}
                        mt="1"
                        fontSize="xs"
                        lineHeight="1.35"
                        color="ui.mutedText"
                      >
                        {t("tabs.directory.description")}
                      </Text>
                    </Box>
                  </Flex>
                </Tabs.Trigger>
              </Tabs.List>
            </Box>
          </SearchHeader>

          <Box pt="0">
            <Suspense
              fallback={
                <CreatorsSearchTabFallback
                  showResults={activeTab === "direct-search"}
                />
              }
            >
              {activeTab === "direct-search" ? (
                <DirectCreatorsSearchTab
                  clearJobErrors={clearJobErrors}
                  expiredJobsError={expiredJobsError}
                  expiredJobsMutation={expiredJobsMutation}
                  missingJobsError={missingJobsError}
                  missingJobsMutation={missingJobsMutation}
                  onOpenHistory={() => setIsHistoryOpen(true)}
                  onUsernamesChange={setUsernames}
                  persistSearchHistoryEntry={persistSearchHistoryEntry}
                  usernames={usernames}
                />
              ) : isBillingPending ? (
                <CreatorsSearchTabFallback showResults={false} />
              ) : isDirectoryLocked ? (
                <DirectoryPaywallPanel
                  trialEligible={billing?.trial_eligible ?? false}
                />
              ) : (
                <CreatorsDirectoryPreview />
              )}
            </Suspense>
          </Box>
        </Tabs.Root>
      </Box>

      <CurrentJobDetailDialog
        job={selectedCurrentJob}
        onOpenChange={(open) => {
          if (!open) {
            clearSelectedCurrentJob()
          }
        }}
        onReuseReadyUsernames={handleReuseReadyUsernames}
      />
      <CurrentJobsDialog
        jobs={currentJobs}
        open={isJobsDialogOpen}
        onOpenChange={setIsJobsDialogOpen}
        onSelectJob={handleSelectJob}
      />
      <SearchHistoryDialog
        items={viewAllQuery.data?.items ?? []}
        loading={viewAllQuery.isLoading}
        open={isHistoryOpen}
        onOpenChange={setIsHistoryOpen}
        onReuseReadyUsernames={handleReuseReadyUsernames}
      />
    </Box>
  )
}
