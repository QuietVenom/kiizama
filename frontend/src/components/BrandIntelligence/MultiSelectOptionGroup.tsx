import {
  chakra,
  Grid,
  Text,
  useFieldContext,
  VisuallyHidden,
} from "@chakra-ui/react"

type MultiSelectOption = {
  description?: string
  label: string
  value: string
}

type MultiSelectOptionGroupProps = {
  disabled?: boolean
  maxSelections?: number
  onChange: (value: string[]) => void
  options: MultiSelectOption[]
  value: string[]
}

const MultiSelectOptionGroup = ({
  disabled,
  maxSelections,
  onChange,
  options,
  value,
}: MultiSelectOptionGroupProps) => {
  const field = useFieldContext()
  const selectedValues = new Set(value)
  const hasReachedLimit =
    typeof maxSelections === "number" && value.length >= maxSelections

  const toggleValue = (nextValue: string) => {
    if (disabled) return

    if (selectedValues.has(nextValue)) {
      onChange(value.filter((item) => item !== nextValue))
      return
    }

    if (hasReachedLimit) {
      return
    }

    onChange([...value, nextValue])
  }

  return (
    <>
      <VisuallyHidden asChild>
        <input
          aria-hidden="true"
          id={field?.ids.control}
          readOnly
          required={false}
          tabIndex={-1}
          value={value.join(",")}
        />
      </VisuallyHidden>

      <Grid
        aria-describedby={field?.ariaDescribedby}
        aria-labelledby={field?.ids.label}
        role="group"
        templateColumns={{ base: "1fr", md: "repeat(2, 1fr)" }}
        gap={3}
      >
        {options.map((option) => {
          const isSelected = selectedValues.has(option.value)
          const isBlocked = disabled || (!isSelected && hasReachedLimit)

          return (
            <chakra.button
              key={option.value}
              type="button"
              textAlign="left"
              rounded="2xl"
              borderWidth="1px"
              borderColor={isSelected ? "ui.brandBorderSoft" : "ui.border"}
              bg={isSelected ? "ui.brandSoft" : "ui.panel"}
              px={4}
              py={4}
              opacity={isBlocked ? 0.55 : 1}
              transition="border-color 180ms ease, background-color 180ms ease, transform 180ms ease"
              _hover={
                isBlocked
                  ? undefined
                  : {
                      borderColor: isSelected
                        ? "ui.brandBorderSoft"
                        : "ui.link",
                      bg: isSelected ? "ui.brandSoft" : "ui.surfaceSoft",
                      transform: "translateY(-1px)",
                    }
              }
              onClick={() => toggleValue(option.value)}
            >
              <Text
                fontWeight="bold"
                color={isSelected ? "ui.brandText" : "ui.text"}
              >
                {option.label}
              </Text>
              {option.description ? (
                <Text mt={1.5} color="ui.secondaryText" fontSize="sm">
                  {option.description}
                </Text>
              ) : null}
            </chakra.button>
          )
        })}
      </Grid>
    </>
  )
}

export default MultiSelectOptionGroup
