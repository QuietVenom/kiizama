import { Badge, Box, Flex, Heading, Text } from "@chakra-ui/react"
import { useTranslation } from "react-i18next"

import {
  type CreatorsSearchLocalJob,
  getCreatorsSearchJobProgressText,
  getCreatorsSearchJobStatusLabel,
} from "@/lib/creators-search-jobs"

import { getJobStatusStyles } from "./creators-search.logic"

export const CurrentJobsPanel = ({
  currentJobs,
  onSelectJob,
}: {
  currentJobs: CreatorsSearchLocalJob[]
  onSelectJob: (jobId: string) => void
}) => {
  const { t } = useTranslation("creatorsSearch")

  return (
    <Box layerStyle="dashboardCard" p={{ base: 6, md: 8 }}>
      <Text
        fontSize="sm"
        color="ui.mutedText"
        fontWeight="bold"
        letterSpacing="0.08em"
      >
        {t("jobs.eyebrow")}
      </Text>
      <Flex mt={2} alignItems="center" justifyContent="space-between" gap={3}>
        <Heading size="md">{t("jobs.title")}</Heading>
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
      <Text mt={3} color="ui.secondaryText" fontSize="sm">
        {t("jobs.description")}
      </Text>

      <Flex
        mt={5}
        direction="column"
        gap={3}
        maxH="560px"
        overflowY="auto"
        pr={1}
      >
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
            const visibleUsernames = job.requestedUsernames.slice(0, 5)
            const hiddenUsernamesCount = Math.max(
              job.requestedUsernames.length - visibleUsernames.length,
              0,
            )
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
                px={4}
                py={4}
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
                  gap={3}
                >
                  <Box minW={0}>
                    <Text
                      color={statusStyles.textColor}
                      fontSize="xs"
                      fontWeight="black"
                      lineClamp={2}
                    >
                      {job.jobId}
                    </Text>
                  </Box>

                  <Badge
                    rounded="full"
                    borderWidth="1px"
                    borderColor="rgba(255,255,255,0.18)"
                    bg="ui.panel"
                    color={statusStyles.textColor}
                    px={3}
                    py={1.5}
                  >
                    {getCreatorsSearchJobStatusLabel(job.status, (key) =>
                      t(key),
                    )}
                  </Badge>
                </Flex>

                <Flex mt={3} gap={2} wrap="wrap">
                  {visibleUsernames.map((username) => (
                    <Badge
                      key={`${job.jobId}-${username}`}
                      rounded="full"
                      borderWidth="1px"
                      borderColor="ui.borderSoft"
                      bg="ui.panel"
                      color="ui.text"
                      px={2.0}
                      py={0.5}
                      fontSize="2xs"
                    >
                      @{username}
                    </Badge>
                  ))}
                  {hiddenUsernamesCount > 0 ? (
                    <Badge
                      rounded="full"
                      borderWidth="1px"
                      borderColor="ui.borderSoft"
                      bg="ui.panel"
                      color="ui.secondaryText"
                      px={2.5}
                      py={1}
                      fontSize="xs"
                    >
                      +{hiddenUsernamesCount}
                    </Badge>
                  ) : null}
                </Flex>

                {job.error ? (
                  <Text mt={3} color={statusStyles.textColor} fontSize="sm">
                    {job.error}
                  </Text>
                ) : null}

                <Text mt={3} color="ui.secondaryText" fontSize="sm">
                  {getCreatorsSearchJobProgressText({
                    canOpenDetail,
                    t: (key) => t(key),
                  })}
                </Text>
              </Box>
            )
          })
        )}
      </Flex>
    </Box>
  )
}
