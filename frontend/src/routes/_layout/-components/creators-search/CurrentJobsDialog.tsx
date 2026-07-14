import { Badge, Box, Flex, Text } from "@chakra-ui/react"
import { useTranslation } from "react-i18next"

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
  MAX_CREATORS_SEARCH_JOBS,
} from "@/lib/creators-search-jobs"

import { CurrentJobCard } from "./CurrentJobCard"

export const CurrentJobsDialog = ({
  jobs,
  onOpenChange,
  onSelectJob,
  open,
}: {
  jobs: CreatorsSearchLocalJob[]
  onOpenChange: (open: boolean) => void
  onSelectJob: (jobId: string) => void
  open: boolean
}) => {
  const { t } = useTranslation(["creatorsSearch", "common"])

  return (
    <DialogRoot
      open={open}
      placement="center"
      onOpenChange={({ open: nextOpen }) => onOpenChange(nextOpen)}
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
          <Flex alignItems="center" justifyContent="space-between" gap={3}>
            <DialogTitle
              display="inline-flex"
              alignItems="center"
              minH="10"
              fontSize={{ base: "xl", md: "2xl" }}
              fontWeight="black"
              letterSpacing="-0.02em"
              lineHeight="1"
              whiteSpace="nowrap"
            >
              {t("creatorsSearch:jobs.dialog.title")}
            </DialogTitle>
            <Badge
              rounded="full"
              borderWidth="1px"
              borderColor="ui.borderSoft"
              bg="ui.surfaceSoft"
              color="ui.secondaryText"
              px={3}
              py={1.5}
            >
              {t("creatorsSearch:jobs.count", {
                count: jobs.length,
                max: MAX_CREATORS_SEARCH_JOBS,
              })}
            </Badge>
          </Flex>
          <Text mt={2} color="ui.secondaryText">
            {t("creatorsSearch:jobs.dialog.description")}
          </Text>
        </DialogHeader>

        <DialogBody
          px={{ base: 5, md: 6 }}
          py={{ base: 5, md: 6 }}
          overflowY="auto"
        >
          {jobs.length === 0 ? (
            <Box
              rounded="2xl"
              borderWidth="1px"
              borderColor="ui.border"
              bg="ui.surfaceSoft"
              px={4}
              py={4}
            >
              <Text color="ui.secondaryText" fontSize="sm" fontWeight="bold">
                {t("creatorsSearch:jobs.empty")}
              </Text>
            </Box>
          ) : (
            <Flex direction="column" gap={3}>
              {jobs.map((job) => (
                <CurrentJobCard
                  key={job.jobId}
                  fullWidth
                  job={job}
                  onSelect={onSelectJob}
                />
              ))}
            </Flex>
          )}
        </DialogBody>

        <DialogFooter
          borderTopWidth="1px"
          borderTopColor="ui.border"
          bg="ui.panel"
          px={{ base: 5, md: 6 }}
          py={4}
        >
          <Button variant="outline" onClick={() => onOpenChange(false)}>
            {t("common:actions.close")}
          </Button>
        </DialogFooter>
      </DialogContent>
    </DialogRoot>
  )
}
