import {
  Badge,
  Box,
  Grid,
  IconButton,
  Portal,
  Text,
  Tooltip,
} from "@chakra-ui/react"
import { useTranslation } from "react-i18next"
import { FiInfo, FiSearch } from "react-icons/fi"

import UsernameTagsInput from "@/components/CreatorsSearch/UsernameTagsInput"
import { Button } from "@/components/ui/button"
import { Field } from "@/components/ui/field"

export const SearchInputPanel = ({
  expiredSet,
  hasValidationIssue,
  invalidSet,
  invalidUsernames,
  isSearchPending,
  isSearchStale,
  maxUsernames,
  missingSet,
  onMaxExceeded,
  onSearch,
  onUsernamesChange,
  usernames,
  validationMessage,
}: {
  expiredSet: ReadonlySet<string>
  hasValidationIssue: boolean
  invalidSet: ReadonlySet<string>
  invalidUsernames: string[]
  isSearchPending: boolean
  isSearchStale: boolean
  maxUsernames: number
  missingSet: ReadonlySet<string>
  onMaxExceeded: () => void
  onSearch: () => void
  onUsernamesChange: (value: string[]) => void
  usernames: string[]
  validationMessage?: string
}) => {
  const { t } = useTranslation("creatorsSearch")

  return (
    <Box
      layerStyle="dashboardCard"
      p={{ base: 5, md: 6, lg: 7 }}
      display="flex"
      flexDirection="column"
      h="100%"
    >
      <Box>
        <Grid
          templateColumns={{ base: "1fr auto", md: "minmax(0, 1fr) auto" }}
          alignItems="start"
          gap={3}
        >
          <Text textStyle="eyebrow" flex="1" minW={0}>
            {t("input.title")}
          </Text>
          <Tooltip.Root openDelay={160} positioning={{ placement: "top" }}>
            <Tooltip.Trigger asChild>
              <IconButton
                aria-label={t("input.helpAria")}
                variant="ghost"
                size="sm"
                color="ui.mutedText"
                _hover={{ bg: "ui.surfaceSoft", color: "ui.text" }}
              >
                <FiInfo />
              </IconButton>
            </Tooltip.Trigger>
            <Portal>
              <Tooltip.Positioner>
                <Tooltip.Content
                  maxW="320px"
                  rounded="2xl"
                  borderWidth="1px"
                  borderColor="ui.border"
                  bg="ui.panel"
                  px={4}
                  py={3}
                  color="ui.text"
                  boxShadow="lg"
                >
                  <Tooltip.Arrow>
                    <Tooltip.ArrowTip />
                  </Tooltip.Arrow>
                  <Text fontSize="sm" lineHeight="1.7">
                    {t("input.tooltip")}
                  </Text>
                </Tooltip.Content>
              </Tooltip.Positioner>
            </Portal>
          </Tooltip.Root>
        </Grid>
        <Button
          mt={4}
          w="full"
          layerStyle="brandGradientButton"
          loading={isSearchPending}
          onClick={onSearch}
          alignSelf="stretch"
          disabled={
            usernames.length === 0 ||
            invalidUsernames.length > 0 ||
            isSearchPending
          }
        >
          <FiSearch />
          {t("input.searchButton")}
        </Button>
      </Box>

      <Field
        mt={5}
        flex="1"
        label={
          <Box w="full">
            <Grid
              templateColumns={{ base: "1fr", md: "minmax(0, 1fr) auto" }}
              alignItems="center"
              gap={3}
            >
              <Text>{t("input.label")}</Text>
              <Badge
                rounded="full"
                borderWidth="1px"
                borderColor="ui.borderSoft"
                bg="ui.surfaceSoft"
                color="ui.secondaryText"
                px={3}
                py={1.5}
                flexShrink={0}
                textAlign="center"
                whiteSpace="nowrap"
              >
                {t("input.count", {
                  count: usernames.length,
                  max: maxUsernames,
                })}
              </Badge>
            </Grid>
            {isSearchStale ? (
              <Box
                mt={3}
                display="inline-flex"
                alignSelf="center"
                justifyContent="center"
                maxW="min(100%, 32rem)"
                rounded="full"
                bg="ui.infoSoft"
                px={4}
                py={2}
              >
                <Text
                  color="ui.infoText"
                  fontSize="sm"
                  fontWeight="medium"
                  lineHeight="1.4"
                  textAlign="center"
                  textWrap="balance"
                >
                  {t("input.staleBadge")}
                </Text>
              </Box>
            ) : null}
          </Box>
        }
        errorText={validationMessage}
        invalid={hasValidationIssue}
      >
        <UsernameTagsInput
          expiredValues={expiredSet}
          invalid={hasValidationIssue}
          invalidValues={invalidSet}
          missingValues={missingSet}
          onMaxExceeded={onMaxExceeded}
          onValueChange={onUsernamesChange}
          placeholder={t("input.placeholder")}
          value={usernames}
        />
      </Field>
    </Box>
  )
}
