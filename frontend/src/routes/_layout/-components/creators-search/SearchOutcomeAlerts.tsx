import { Badge, Box, Flex, Icon, Text } from "@chakra-ui/react"
import { useTranslation } from "react-i18next"
import { FiAlertCircle, FiSearch } from "react-icons/fi"

import { Button } from "@/components/ui/button"

type JobsMutation = {
  isPending: boolean
  mutate: (usernames: string[]) => void
}

const ErrorAlert = ({ message, title }: { message: string; title: string }) => (
  <Box
    mb={{ base: 6, lg: 7 }}
    rounded="3xl"
    borderWidth="1px"
    borderColor="ui.danger"
    bg="ui.dangerSoft"
    px={{ base: 5, md: 6 }}
    py={{ base: 4, md: 5 }}
  >
    <Flex alignItems="flex-start" gap={3}>
      <Flex
        boxSize="10"
        flexShrink={0}
        alignItems="center"
        justifyContent="center"
        rounded="2xl"
        bg="rgba(220, 38, 38, 0.10)"
        color="ui.dangerText"
      >
        <Icon as={FiAlertCircle} boxSize={5} />
      </Flex>
      <Box>
        <Text color="ui.dangerText" fontWeight="black">
          {title}
        </Text>
        <Text mt={1} color="ui.secondaryText">
          {message}
        </Text>
      </Box>
    </Flex>
  </Box>
)

export const SearchOutcomeAlerts = ({
  expiredJobsError,
  expiredJobsMutation,
  expiredUsernames,
  missingJobsError,
  missingJobsMutation,
  missingUsernames,
  reportError,
  searchError,
}: {
  expiredJobsError: string | null
  expiredJobsMutation: JobsMutation
  expiredUsernames: string[]
  missingJobsError: string | null
  missingJobsMutation: JobsMutation
  missingUsernames: string[]
  reportError: string | null
  searchError: string | null
}) => {
  const { t } = useTranslation(["creatorsSearch", "common"])

  return (
    <>
      {searchError ? (
        <ErrorAlert
          title={t("creatorsSearch:alerts.searchFailed")}
          message={searchError}
        />
      ) : null}

      {reportError ? (
        <ErrorAlert
          title={t("creatorsSearch:alerts.reportFailed")}
          message={reportError}
        />
      ) : null}

      {expiredUsernames.length > 0 ? (
        <Box
          mb={{ base: 6, lg: 7 }}
          rounded="3xl"
          borderWidth="1px"
          borderColor="ui.warning"
          bg="ui.warningSoft"
          px={{ base: 5, md: 6 }}
          py={{ base: 5, md: 6 }}
        >
          <Text color="ui.warningText" fontSize="lg" fontWeight="black">
            {t("creatorsSearch:alerts.expired.title")}
          </Text>
          <Flex
            mt={2}
            alignItems={{ base: "stretch", md: "flex-start" }}
            justifyContent="space-between"
            gap={3}
            direction={{ base: "column", md: "row" }}
          >
            <Text color="ui.secondaryText">
              {t("creatorsSearch:alerts.expired.description")}
            </Text>
            <Button
              flexShrink={0}
              loading={expiredJobsMutation.isPending}
              onClick={() => expiredJobsMutation.mutate(expiredUsernames)}
              disabled={
                expiredUsernames.length === 0 || expiredJobsMutation.isPending
              }
            >
              <FiSearch />
              {t("common:actions.search")}
            </Button>
          </Flex>

          {expiredJobsError ? (
            <Text mt={3} color="ui.warningText" fontSize="sm" fontWeight="bold">
              {expiredJobsError}
            </Text>
          ) : null}

          <Flex mt={4} gap={2} wrap="wrap">
            {expiredUsernames.map((username) => (
              <Badge
                key={username}
                rounded="full"
                borderWidth="1px"
                borderColor="ui.warning"
                bg="ui.panel"
                color="ui.warningText"
                px={3}
                py={1.5}
              >
                @{username}
              </Badge>
            ))}
          </Flex>
        </Box>
      ) : null}

      {missingUsernames.length > 0 ? (
        <Box
          mb={{ base: 6, lg: 7 }}
          rounded="3xl"
          borderWidth="1px"
          borderColor="ui.danger"
          bg="ui.dangerSoft"
          px={{ base: 5, md: 6 }}
          py={{ base: 5, md: 6 }}
        >
          <Text color="ui.dangerText" fontSize="lg" fontWeight="black">
            {t("creatorsSearch:alerts.missing.title")}
          </Text>
          <Flex
            mt={2}
            alignItems={{ base: "stretch", md: "flex-start" }}
            justifyContent="space-between"
            gap={3}
            direction={{ base: "column", md: "row" }}
          >
            <Text color="ui.secondaryText" maxW="56ch">
              {t("creatorsSearch:alerts.missing.description")}
            </Text>
            <Button
              flexShrink={0}
              loading={missingJobsMutation.isPending}
              onClick={() => missingJobsMutation.mutate(missingUsernames)}
              disabled={
                missingUsernames.length === 0 || missingJobsMutation.isPending
              }
            >
              <FiSearch />
              {t("common:actions.search")}
            </Button>
          </Flex>

          {missingJobsError ? (
            <Text mt={3} color="ui.dangerText" fontSize="sm" fontWeight="bold">
              {missingJobsError}
            </Text>
          ) : null}

          <Flex mt={4} gap={2} wrap="wrap">
            {missingUsernames.map((username) => (
              <Badge
                key={username}
                rounded="full"
                borderWidth="1px"
                borderColor="ui.danger"
                bg="ui.panel"
                color="ui.dangerText"
                px={3}
                py={1.5}
              >
                @{username}
              </Badge>
            ))}
          </Flex>
        </Box>
      ) : null}
    </>
  )
}
