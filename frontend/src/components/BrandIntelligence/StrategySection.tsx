import { Box, Text } from "@chakra-ui/react"
import type { ReactNode } from "react"

type StrategySectionProps = {
  children: ReactNode
  description: string
  eyebrow: string
  title: string
}

const StrategySection = ({
  children,
  description,
  eyebrow,
  title,
}: StrategySectionProps) => {
  return (
    <Box
      rounded="3xl"
      borderWidth="1px"
      borderColor="ui.border"
      bg="ui.panel"
      px={{ base: 5, md: 6 }}
      py={{ base: 5, md: 6 }}
    >
      <Text
        fontSize="xs"
        fontWeight="bold"
        color="ui.mutedText"
        letterSpacing="0.08em"
        textTransform="uppercase"
      >
        {eyebrow}
      </Text>
      <Text mt={2} fontSize={{ base: "lg", lg: "xl" }} fontWeight="black">
        {title}
      </Text>
      <Text mt={2} color="ui.secondaryText" maxW="62ch">
        {description}
      </Text>
      <Box mt={5}>{children}</Box>
    </Box>
  )
}

export default StrategySection
