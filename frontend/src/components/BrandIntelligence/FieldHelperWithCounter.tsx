import { Flex, Text } from "@chakra-ui/react"

type FieldHelperWithCounterProps = {
  count: number
  helperText?: string
  limit: number
}

const FieldHelperWithCounter = ({
  count,
  helperText,
  limit,
}: FieldHelperWithCounterProps) => {
  const counterColor =
    count > limit
      ? "ui.dangerText"
      : count >= Math.floor(limit * 0.9)
        ? "ui.warningText"
        : "ui.mutedText"

  return (
    <Flex
      justifyContent="space-between"
      alignItems="center"
      gap={3}
      wrap="wrap"
    >
      <Text color="ui.mutedText">{helperText ?? " "}</Text>
      <Text color={counterColor} fontSize="sm" fontWeight="semibold">
        {count} / {limit}
      </Text>
    </Flex>
  )
}

export default FieldHelperWithCounter
