import { Badge, Box, Flex, Icon, Text } from "@chakra-ui/react"
import { useTranslation } from "react-i18next"
import { FiEye } from "react-icons/fi"

import {
  type CreatorsSearchLocalJob,
  getCreatorsSearchJobStatusLabel,
} from "@/lib/creators-search-jobs"

import { getJobStatusStyles } from "./creators-search.logic"

export const CurrentJobCard = ({
  fullWidth = false,
  job,
  onSelect,
}: {
  fullWidth?: boolean
  job: CreatorsSearchLocalJob
  onSelect: (jobId: string) => void
}) => {
  const { t } = useTranslation("creatorsSearch")
  const statusStyles = getJobStatusStyles(job.status)
  const canOpenDetail =
    (job.status === "done" || job.status === "failed") &&
    (job.terminalPayload !== null ||
      job.readyUsernames.length > 0 ||
      Boolean(job.error))

  return (
    <Box
      as={canOpenDetail ? "button" : "div"}
      rounded="2xl"
      borderWidth="1px"
      borderColor={statusStyles.borderColor}
      bg={statusStyles.bg}
      px={3.5}
      py={3.5}
      minW={fullWidth ? undefined : { base: "210px", md: "220px" }}
      maxW={fullWidth ? "full" : { base: "240px", md: "240px" }}
      w={fullWidth ? "full" : undefined}
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
      onClick={canOpenDetail ? () => onSelect(job.jobId) : undefined}
    >
      <Flex alignItems="flex-start" justifyContent="space-between" gap={2}>
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

      <Flex mt={2.5} alignItems="center" justifyContent="space-between" gap={2}>
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
          {getCreatorsSearchJobStatusLabel(job.status, (key) => t(key))}
        </Badge>
        <Text color="ui.secondaryText" fontSize="xs" fontWeight="bold">
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
}
