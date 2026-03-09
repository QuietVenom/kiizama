import { TagsInput } from "@ark-ui/react"
import { Box, Flex, Input, Tag } from "@chakra-ui/react"
import { FiX } from "react-icons/fi"

const MAX_USERNAMES = 50

type UsernameTagsInputProps = {
  disabled?: boolean
  expiredValues?: ReadonlySet<string>
  invalid?: boolean
  invalidValues?: ReadonlySet<string>
  missingValues?: ReadonlySet<string>
  onMaxExceeded?: () => void
  onValueChange: (value: string[]) => void
  placeholder?: string
  value: string[]
}

const getTagPalette = (
  username: string,
  expiredValues: ReadonlySet<string>,
  invalidValues: ReadonlySet<string>,
  missingValues: ReadonlySet<string>,
) => {
  if (invalidValues.has(username) || missingValues.has(username)) {
    return {
      background: "ui.dangerSoft",
      borderColor: "ui.danger",
      color: "ui.dangerText",
      closeHoverBg: "rgba(220, 38, 38, 0.12)",
    }
  }

  if (expiredValues.has(username)) {
    return {
      background: "ui.warningSoft",
      borderColor: "ui.warning",
      color: "ui.warningText",
      closeHoverBg: "rgba(217, 119, 6, 0.12)",
    }
  }

  return {
    background: "ui.brandSoft",
    borderColor: "ui.brandBorderSoft",
    color: "ui.brandText",
    closeHoverBg: "rgba(249, 115, 22, 0.10)",
  }
}

const UsernameTagsInput = ({
  disabled,
  expiredValues = new Set<string>(),
  invalid,
  invalidValues = new Set<string>(),
  missingValues = new Set<string>(),
  onMaxExceeded,
  onValueChange,
  placeholder = "Add usernames and press Enter",
  value,
}: UsernameTagsInputProps) => {
  return (
    <Box w="full">
      <TagsInput.Root
        addOnPaste
        blurBehavior="add"
        delimiter={/[\s,]+/}
        disabled={disabled}
        editable={false}
        invalid={invalid}
        max={MAX_USERNAMES}
        onValueChange={({ value }) => onValueChange(value)}
        onValueInvalid={({ reason }) => {
          if (reason === "rangeOverflow") {
            onMaxExceeded?.()
          }
        }}
        value={value}
        style={{ display: "block", width: "100%" }}
      >
        <TagsInput.HiddenInput />

        <TagsInput.Control asChild>
          <Flex
            minH="58px"
            w="full"
            flexWrap="wrap"
            alignItems="center"
            gap={2}
            rounded="2xl"
            borderWidth="1px"
            borderColor={invalid ? "ui.danger" : "ui.sidebarBorder"}
            bg={disabled ? "ui.surfaceSoft" : "ui.panel"}
            px={3}
            py={3}
            transition="border-color 180ms ease, box-shadow 180ms ease"
            _focusWithin={{
              borderColor: invalid ? "ui.danger" : "ui.brandBorderSoft",
              boxShadow: invalid
                ? "0 0 0 1px var(--chakra-colors-ui-danger)"
                : "0 0 0 1px var(--chakra-colors-ui-brandBorderSoft)",
            }}
          >
            {value.map((username, index) => {
              const palette = getTagPalette(
                username,
                expiredValues,
                invalidValues,
                missingValues,
              )

              return (
                <TagsInput.Item
                  index={index}
                  key={username}
                  value={username}
                  asChild
                >
                  <Tag.Root
                    display="inline-flex"
                    alignItems="center"
                    rounded="full"
                    borderWidth="1px"
                    borderColor={palette.borderColor}
                    bg={palette.background}
                    color={palette.color}
                    px={1.5}
                    py={1.5}
                    gap={1.5}
                    maxW="full"
                  >
                    <TagsInput.ItemPreview asChild>
                      <Tag.Label
                        maxW={{ base: "150px", md: "220px" }}
                        truncate
                        fontWeight="semibold"
                      >
                        @{username}
                      </Tag.Label>
                    </TagsInput.ItemPreview>

                    <TagsInput.ItemDeleteTrigger asChild>
                      <Box
                        as="button"
                        aria-label={`Remove ${username}`}
                        display="inline-flex"
                        alignItems="center"
                        justifyContent="center"
                        boxSize="4.5"
                        flexShrink={0}
                        rounded="full"
                        p="0"
                        color="inherit"
                        lineHeight="0"
                        transition="background 180ms ease"
                        _hover={{ bg: palette.closeHoverBg }}
                      >
                        <Box as={FiX} boxSize="3.5" flexShrink={0} />
                      </Box>
                    </TagsInput.ItemDeleteTrigger>
                  </Tag.Root>
                </TagsInput.Item>
              )
            })}

            <TagsInput.Input asChild>
              <Input
                minW="0"
                w="full"
                flex="1 1 100%"
                borderWidth="0"
                bg="transparent"
                px={1}
                py={0}
                placeholder={placeholder}
                _placeholder={{ color: "ui.mutedText" }}
                _focusVisible={{ boxShadow: "none", outline: "none" }}
              />
            </TagsInput.Input>
          </Flex>
        </TagsInput.Control>
      </TagsInput.Root>
    </Box>
  )
}

export default UsernameTagsInput
