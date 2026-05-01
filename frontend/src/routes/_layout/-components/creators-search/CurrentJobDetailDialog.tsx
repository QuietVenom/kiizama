import { Badge, Box, Flex, SimpleGrid, Text } from "@chakra-ui/react"
import { FiSearch } from "react-icons/fi"

import { Button } from "@/components/ui/button"
import {
  DialogBody,
  DialogContent,
  DialogFooter,
  DialogHeader,
  DialogRoot,
  DialogTitle,
} from "@/components/ui/dialog"
import {
  type CreatorsSearchLocalJob,
  getCreatorsSearchJobStatusLabel,
} from "@/lib/creators-search-jobs"

import { formatJobTimestamp, getJobStatusStyles } from "./creators-search.logic"
import { SearchOverviewCard } from "./SearchOverviewCard"
import { UsernameGroup } from "./UsernameGroup"

export const CurrentJobDetailDialog = ({
  job,
  onOpenChange,
  onReuseReadyUsernames,
}: {
  job: CreatorsSearchLocalJob | null
  onOpenChange: (open: boolean) => void
  onReuseReadyUsernames: (usernames: string[]) => void
}) => {
  const terminalPayload = job?.terminalPayload
  const requestedUsernames =
    terminalPayload?.requested_usernames ?? job?.requestedUsernames ?? []
  const readyUsernames =
    terminalPayload?.ready_usernames ?? job?.readyUsernames ?? []
  const failedUsernames = terminalPayload?.failed_usernames ?? []
  const notFoundUsernames = terminalPayload?.not_found_usernames ?? []
  const skippedUsernames = terminalPayload?.skipped_usernames ?? []
  const successfulUsernames = terminalPayload?.successful_usernames ?? []

  return (
    <DialogRoot
      open={job !== null}
      placement="center"
      onOpenChange={({ open }) => onOpenChange(open)}
    >
      <DialogContent
        maxW={{ base: "calc(100vw - 1rem)", md: "860px" }}
        maxH={{ base: "calc(100vh - 1rem)", md: "calc(100vh - 4rem)" }}
        overflow="hidden"
        rounded="4xl"
        borderWidth="1px"
        borderColor="ui.border"
        bg="ui.page"
      >
        <DialogHeader
          borderBottomWidth="1px"
          borderBottomColor="ui.border"
          bg="ui.panel"
          px={{ base: 6, md: 7 }}
          py={{ base: 6, md: 7 }}
        >
          <DialogTitle
            display="flex"
            alignItems={{ base: "flex-start", md: "center" }}
            justifyContent="space-between"
            gap={3}
            flexDirection={{ base: "column", md: "row" }}
          >
            <Box minW={0}>
              <Text
                color="ui.mutedText"
                fontSize="sm"
                fontWeight="bold"
                letterSpacing="0.08em"
              >
                CURRENT JOB DETAIL
              </Text>
              <Text
                mt={2}
                fontSize={{ base: "lg", md: "xl" }}
                fontWeight="black"
                lineHeight="1.2"
                wordBreak="break-word"
              >
                {job?.jobId ?? "Job detail"}
              </Text>
            </Box>
            {job ? (
              <Badge
                rounded="full"
                borderWidth="1px"
                borderColor={getJobStatusStyles(job.status).borderColor}
                bg="ui.panel"
                color={getJobStatusStyles(job.status).textColor}
                px={3}
                py={1.5}
              >
                {getCreatorsSearchJobStatusLabel(job.status)}
              </Badge>
            ) : null}
          </DialogTitle>
          {job ? (
            <Text mt={2} color="ui.secondaryText">
              {job.sourceBox === "expired"
                ? "Profiles need updates"
                : "Usernames not found"}{" "}
              batch updated {formatJobTimestamp(job.updatedAt)}.
            </Text>
          ) : null}
        </DialogHeader>

        <DialogBody
          px={{ base: 5, md: 6 }}
          py={{ base: 5, md: 6 }}
          overflowY="auto"
        >
          {job ? (
            <Flex direction="column" gap={4}>
              <SimpleGrid columns={{ base: 1, sm: 2, xl: 4 }} gap={3}>
                <SearchOverviewCard
                  label="Requested"
                  tone="brand"
                  value={String(
                    terminalPayload?.counters.requested ??
                      requestedUsernames.length,
                  )}
                />
                <SearchOverviewCard
                  label="Ready"
                  tone="success"
                  value={String(readyUsernames.length)}
                />
                <SearchOverviewCard
                  label="Failed"
                  tone="danger"
                  value={String(
                    terminalPayload?.counters.failed ?? failedUsernames.length,
                  )}
                />
                <SearchOverviewCard
                  label="Not found"
                  tone="warning"
                  value={String(
                    terminalPayload?.counters.not_found ??
                      notFoundUsernames.length,
                  )}
                />
              </SimpleGrid>

              <UsernameGroup
                title="Requested usernames"
                tone="neutral"
                usernames={requestedUsernames}
              />
              <UsernameGroup
                title="Ready usernames"
                tone="success"
                usernames={readyUsernames}
              />
              <UsernameGroup
                title="Successful usernames"
                tone="success"
                usernames={successfulUsernames}
              />
              <UsernameGroup
                title="Skipped usernames"
                tone="warning"
                usernames={skippedUsernames}
              />
              <UsernameGroup
                title="Failed usernames"
                tone="danger"
                usernames={failedUsernames}
              />
              <UsernameGroup
                title="Not found usernames"
                tone="warning"
                usernames={notFoundUsernames}
              />

              {job.error ? (
                <Box
                  rounded="2xl"
                  borderWidth="1px"
                  borderColor="ui.danger"
                  bg="ui.dangerSoft"
                  px={4}
                  py={4}
                >
                  <Text color="ui.dangerText" fontWeight="black">
                    Worker error
                  </Text>
                  <Text mt={2} color="ui.secondaryText" fontSize="sm">
                    {job.error}
                  </Text>
                </Box>
              ) : null}
            </Flex>
          ) : null}
        </DialogBody>

        <DialogFooter
          borderTopWidth="1px"
          borderTopColor="ui.border"
          bg="ui.panel"
          px={{ base: 5, md: 6 }}
          py={4}
          justifyContent="space-between"
          gap={3}
          flexDirection={{ base: "column-reverse", md: "row" }}
        >
          <Button variant="outline" onClick={() => onOpenChange(false)}>
            Close
          </Button>
          {job && readyUsernames.length > 0 ? (
            <Button
              layerStyle="brandGradientButton"
              onClick={() => onReuseReadyUsernames(readyUsernames)}
            >
              <FiSearch />
              Search
            </Button>
          ) : null}
        </DialogFooter>
      </DialogContent>
    </DialogRoot>
  )
}
