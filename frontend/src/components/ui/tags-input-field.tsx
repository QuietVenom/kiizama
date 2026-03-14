import { TagsInput } from "@ark-ui/react"
import { Box, Flex, Input, Tag } from "@chakra-ui/react"
import { FiX } from "react-icons/fi"

type TagPalette = {
  background: string
  borderColor: string
  color: string
  closeHoverBg: string
}

type TagsInputFieldProps = {
  delimiter?: RegExp
  disabled?: boolean
  getTagPalette?: (value: string) => TagPalette
  invalid?: boolean
  inputMaxLength?: number
  inputValue?: string
  max?: number
  onMaxExceeded?: () => void
  onInputValueChange?: (value: string) => void
  onValueChange: (value: string[]) => void
  placeholder?: string
  renderTagLabel?: (value: string) => string
  value: string[]
}

const defaultTagPalette: TagPalette = {
  background: "ui.brandSoft",
  borderColor: "ui.brandBorderSoft",
  color: "ui.brandText",
  closeHoverBg: "rgba(249, 115, 22, 0.10)",
}

export const TagsInputField = ({
  delimiter = /[\s,]+/,
  disabled,
  getTagPalette,
  invalid,
  inputMaxLength,
  inputValue,
  max,
  onMaxExceeded,
  onInputValueChange,
  onValueChange,
  placeholder = "Add items and press Enter",
  renderTagLabel,
  value,
}: TagsInputFieldProps) => {
  return (
    <Box w="full">
      <TagsInput.Root
        addOnPaste
        blurBehavior="add"
        delimiter={delimiter}
        disabled={disabled}
        editable={false}
        inputValue={inputValue}
        invalid={invalid}
        max={max}
        maxLength={inputMaxLength}
        required={false}
        onInputValueChange={({ inputValue }) => onInputValueChange?.(inputValue)}
        onValueChange={({ value }) => onValueChange(value)}
        onValueInvalid={({ reason }) => {
          if (reason === "rangeOverflow") {
            onMaxExceeded?.()
          }
        }}
        value={value}
        style={{ display: "block", width: "100%" }}
      >
        <TagsInput.HiddenInput required={false} />

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
            {value.map((item, index) => {
              const palette = getTagPalette?.(item) ?? defaultTagPalette

              return (
                <TagsInput.Item index={index} key={item} value={item} asChild>
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
                        {renderTagLabel?.(item) ?? item}
                      </Tag.Label>
                    </TagsInput.ItemPreview>

                    <TagsInput.ItemDeleteTrigger asChild>
                      <Box
                        as="button"
                        aria-label={`Remove ${item}`}
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

            <TagsInput.Input asChild required={false}>
              <Input
                minW="0"
                w="full"
                flex="1 1 100%"
                borderWidth="0"
                bg="transparent"
                px={1}
                py={0}
                maxLength={inputMaxLength}
                placeholder={placeholder}
                required={false}
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
