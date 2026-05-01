import {
  Badge,
  Box,
  Flex,
  Heading,
  IconButton,
  Portal,
  Text,
  Tooltip,
} from "@chakra-ui/react"
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
}) => (
  <Box
    layerStyle="dashboardCard"
    p={{ base: 5, md: 6, lg: 7 }}
    display="flex"
    flexDirection="column"
    h="100%"
  >
    <Box>
      <Text
        fontSize="sm"
        color="ui.mutedText"
        fontWeight="bold"
        letterSpacing="0.08em"
      >
        MULTI-USERNAME LOOKUP
      </Text>
      <Flex mt={2} alignItems="center" gap={2} wrap="wrap">
        <Heading size="lg">Search creators by username</Heading>
        <Tooltip.Root openDelay={160} positioning={{ placement: "top" }}>
          <Tooltip.Trigger asChild>
            <IconButton
              aria-label="Search help"
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
                  Paste a list, press Enter, or separate usernames with commas.
                  Usernames are normalized to lowercase and any leading @ is
                  removed automatically before the search runs.
                </Text>
              </Tooltip.Content>
            </Tooltip.Positioner>
          </Portal>
        </Tooltip.Root>
      </Flex>
    </Box>

    <Field
      mt={5}
      flex="1"
      label="Instagram usernames"
      helperText={
        hasValidationIssue ? undefined : "Up to 50 usernames per request."
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
        placeholder="creator_one, brand.partner, another_creator"
        value={usernames}
      />
    </Field>

    <Flex
      alignItems={{ base: "stretch", md: "center" }}
      justifyContent="space-between"
      gap={3}
      direction={{ base: "column", md: "row" }}
      mt="auto"
      pt={6}
    >
      <Flex alignItems="center" gap={2} wrap="wrap">
        <Badge
          rounded="full"
          borderWidth="1px"
          borderColor="ui.borderSoft"
          bg="ui.surfaceSoft"
          color="ui.secondaryText"
          px={3}
          py={1.5}
        >
          {usernames.length} / {maxUsernames} usernames
        </Badge>
        {isSearchStale ? (
          <Badge
            rounded="full"
            bg="ui.infoSoft"
            color="ui.infoText"
            px={3}
            py={1.5}
          >
            Input changed, search again to refresh
          </Badge>
        ) : null}
      </Flex>

      <Button
        layerStyle="brandGradientButton"
        loading={isSearchPending}
        onClick={onSearch}
        alignSelf={{ base: "stretch", md: "flex-start" }}
        disabled={
          usernames.length === 0 ||
          invalidUsernames.length > 0 ||
          isSearchPending
        }
      >
        <FiSearch />
        Search creators
      </Button>
    </Flex>
  </Box>
)
