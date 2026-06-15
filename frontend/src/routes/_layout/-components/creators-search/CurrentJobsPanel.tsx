import { Badge, Box, Flex, Icon, Text } from "@chakra-ui/react"
import { useTranslation } from "react-i18next"
import { FiChevronDown, FiChevronRight, FiEye } from "react-icons/fi"

import {
  type CreatorsSearchLocalJob,
  getCreatorsSearchJobStatusLabel,
} from "@/lib/creators-search-jobs"

import { getJobStatusStyles } from "./creators-search.logic"

export const CurrentJobsPanel = ({
  collapsed = false,
  currentJobs,
  onSelectJob,
  onToggleCollapsed,
}: {
  collapsed?: boolean
  currentJobs: CreatorsSearchLocalJob[]
  onSelectJob: (jobId: string) => void
  onToggleCollapsed?: () => void
}) => {
  const { t } = useTranslation("creatorsSearch")

  return (
    <Box layerStyle="dashboardCard" p={{ base: 5, md: 6 }}>
      <Flex
        as={onToggleCollapsed ? "button" : "div"}
        w="full"
        alignItems="center"
        justifyContent="space-between"
        gap={3}
        textAlign="left"
        onClick={onToggleCollapsed}
      >
        <Flex alignItems="center" gap={2.5}>
          <Icon
            as={collapsed ? FiChevronRight : FiChevronDown}
            boxSize={4}
            color="ui.mutedText"
          />
          <Text textStyle="eyebrow">{t("jobs.title")}</Text>
        </Flex>
        <Badge
          rounded="full"
          borderWidth="1px"
          borderColor="ui.borderSoft"
          bg="ui.surfaceSoft"
          color="ui.secondaryText"
          px={3}
          py={1.5}
        >
          {t("jobs.count", { count: currentJobs.length, max: 10 })}
        </Badge>
      </Flex>

      {collapsed ? null : (
        <Flex mt={4} gap={3} overflowX="auto" overflowY="hidden" pb={1}>
          {currentJobs.length === 0 ? (
            <Box
              rounded="2xl"
              borderWidth="1px"
              borderColor="ui.border"
              bg="ui.surfaceSoft"
              px={4}
              py={4}
            >
              <Text color="ui.secondaryText" fontSize="sm" fontWeight="bold">
                {t("jobs.empty")}
              </Text>
            </Box>
          ) : (
            currentJobs.map((job) => {
              const statusStyles = getJobStatusStyles(job.status)
              const canOpenDetail =
                (job.status === "done" || job.status === "failed") &&
                (job.terminalPayload !== null ||
                  job.readyUsernames.length > 0 ||
                  Boolean(job.error))

              return (
                <Box
                  key={job.jobId}
                  as={canOpenDetail ? "button" : "div"}
                  rounded="2xl"
                  borderWidth="1px"
                  borderColor={statusStyles.borderColor}
                  bg={statusStyles.bg}
                  px={3.5}
                  py={3.5}
                  minW={{ base: "210px", md: "220px" }}
                  maxW={{ base: "240px", md: "240px" }}
                  textAlign="left"
                  transition="transform 180ms ease, box-shadow 180ms ease"
                  cursor={canOpenDetail ? "pointer" : "default"}
                  _hover={
                    canOpenDetail
                      ? {
                          boxShadow: "md",
                        }
                      : undefined
                  }
                  onClick={
                    canOpenDetail ? () => onSelectJob(job.jobId) : undefined
                  }
                >
                  <Flex
                    alignItems="flex-start"
                    justifyContent="space-between"
                    gap={2}
                  >
                    <Box minW={0} flex="1">
                      <Text
                        color={statusStyles.textColor}
                        fontSize="2xs"
                        fontWeight="black"
                        lineClamp={2}
                      >
                        {job.jobId}
                      </Text>
                    </Box>

                    {canOpenDetail ? (
                      <Flex
                        boxSize="7"
                        flexShrink={0}
                        alignItems="center"
                        justifyContent="center"
                        rounded="full"
                        bg="ui.panel"
                        color={statusStyles.textColor}
                      >
                        <Icon as={FiEye} boxSize={3.5} />
                      </Flex>
                    ) : null}
                  </Flex>

                  <Flex
                    mt={2.5}
                    alignItems="center"
                    justifyContent="space-between"
                    gap={2}
                  >
                    <Badge
                      rounded="full"
                      borderWidth="1px"
                      borderColor="rgba(255,255,255,0.18)"
                      bg="ui.panel"
                      color={statusStyles.textColor}
                      px={2.5}
                      py={1}
                      fontSize="2xs"
                    >
                      {getCreatorsSearchJobStatusLabel(job.status, (key) =>
                        t(key),
                      )}
                    </Badge>
                    <Text
                      color="ui.secondaryText"
                      fontSize="xs"
                      fontWeight="bold"
                    >
                      {t("jobs.queries", {
                        count: job.requestedUsernames.length,
                      })}
                    </Text>
                  </Flex>

                  {job.error ? (
                    <Text
                      mt={2.5}
                      color={statusStyles.textColor}
                      fontSize="xs"
                      lineClamp={2}
                    >
                      {job.error}
                    </Text>
                  ) : null}
                </Box>
              )
            })
          )}
        </Flex>
      )}
    </Box>
  )
}
