import { Field as ChakraField, Flex, Text } from "@chakra-ui/react"
import * as React from "react"

export interface FieldProps extends Omit<ChakraField.RootProps, "label"> {
  label?: React.ReactNode
  labelMode?: "label" | "text"
  labelEndElement?: React.ReactNode
  helperText?: React.ReactNode
  errorText?: React.ReactNode
  optionalText?: React.ReactNode
}

export const Field = React.forwardRef<HTMLDivElement, FieldProps>(
  function Field(props, ref) {
    const {
      label,
      labelMode = "label",
      labelEndElement,
      children,
      helperText,
      errorText,
      optionalText,
      ids,
      ...rest
    } = props
    const controlId = ids?.control

    return (
      <ChakraField.Root ref={ref} ids={ids} {...rest}>
        {label && (
          <Flex alignItems="center" gap={1.5}>
            {labelMode === "label" ? (
              <ChakraField.Label htmlFor={controlId}>
                {label}
                <ChakraField.RequiredIndicator fallback={optionalText} />
              </ChakraField.Label>
            ) : (
              <Text fontWeight="medium">{label}</Text>
            )}
            {labelEndElement}
          </Flex>
        )}
        {children}
        {helperText && (
          <ChakraField.HelperText>{helperText}</ChakraField.HelperText>
        )}
        {errorText && (
          <ChakraField.ErrorText>{errorText}</ChakraField.ErrorText>
        )}
      </ChakraField.Root>
    )
  },
)
