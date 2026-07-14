import { Flex, Text } from "@chakra-ui/react"
import { useTranslation } from "react-i18next"

import { Button } from "@/components/ui/button"
import type { CreatorsSearchLocalJob } from "@/lib/creators-search-jobs"

import { CurrentJobCard } from "./CurrentJobCard"

export const CurrentJobsSummary = ({
  currentJobs,
  onSelectJob,
  onViewAll,
}: {
  currentJobs: CreatorsSearchLocalJob[]
  onSelectJob: (jobId: string) => void
  onViewAll: () => void
}) => {
  const { t } = useTranslation("creatorsSearch")

  if (currentJobs.length === 0) {
    return null
  }

  return (
    <Flex
      direction="column"
      gap={2}
      alignSelf={{ base: "stretch", lg: "flex-start" }}
      alignItems={{ base: "stretch", lg: "flex-end" }}
    >
      <Text color="ui.mutedText" fontSize="xs" fontWeight="bold">
        {t("jobs.title")}
      </Text>
      <CurrentJobCard job={currentJobs[0]} onSelect={onSelectJob} />
      {currentJobs.length > 1 ? (
        <Button size="sm" variant="outline" onClick={onViewAll}>
          {t("jobs.viewAll", { count: currentJobs.length })}
        </Button>
      ) : null}
    </Flex>
  )
}
