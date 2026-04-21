import { Box, Flex, Icon, Text } from "@chakra-ui/react"
import type { ReactNode } from "react"
import type { IconType } from "react-icons/lib"

type MetricCardProps = {
  icon: IconType
  label: string
  value: ReactNode
  tone: "info" | "accent" | "positive" | "success"
}

const toneStyles = {
  info: { bg: "ui.infoSoft", color: "ui.infoText" },
  accent: { bg: "ui.accentSoft", color: "ui.accentText" },
  positive: { bg: "ui.positiveSoft", color: "ui.positiveText" },
  success: { bg: "ui.successSoft", color: "ui.successText" },
} as const

const MetricCard = ({ icon, label, value, tone }: MetricCardProps) => {
  const [titlePart, ...labelParts] = label.split(":")
  const title = titlePart.trim()
  const displayLabel = labelParts.join(":").trim() || label
  const toneStyle = toneStyles[tone]

  return (
    <Box layerStyle="dashboardCardInteractive" px={6} py={6} minH="200px">
      <Text
        fontSize="sm"
        color="ui.mutedText"
        fontWeight="bold"
        letterSpacing="0.04em"
        mb={3}
      >
        {title}
      </Text>

      <Flex alignItems="center" gap={3} mb={5}>
        <Flex
          boxSize="14"
          rounded="2xl"
          bg={toneStyle.bg}
          alignItems="center"
          justifyContent="center"
          color={toneStyle.color}
        >
          <Icon as={icon} boxSize={7} />
        </Flex>
        <Text
          fontSize={{ base: "md", lg: "lg" }}
          color="ui.secondaryText"
          fontWeight="bold"
          maxW="30ch"
        >
          {displayLabel}
        </Text>
      </Flex>
      <Text
        fontSize={{ base: "2xl", lg: "3xl" }}
        fontWeight="black"
        textAlign="center"
      >
        {value}
      </Text>
    </Box>
  )
}

export default MetricCard
