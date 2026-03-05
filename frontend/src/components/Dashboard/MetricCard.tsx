import { Box, Flex, Icon, Text } from "@chakra-ui/react"
import type { IconType } from "react-icons/lib"

type MetricCardProps = {
  icon: IconType
  label: string
  value: string
  iconBg: string
  iconColor: string
}

const MetricCard = ({
  icon,
  label,
  value,
  iconBg,
  iconColor,
}: MetricCardProps) => {
  const [titlePart, ...labelParts] = label.split(":")
  const title = titlePart.trim()
  const displayLabel = labelParts.join(":").trim() || label

  return (
    <Box
      bg="white"
      borderWidth="1px"
      borderColor="ui.sidebarBorder"
      rounded="3xl"
      px={6}
      py={6}
      boxShadow="0 4px 20px rgba(15, 23, 42, 0.04)"
      minH="200px"
      transition="transform 220ms ease, box-shadow 220ms ease"
      _hover={{
        transform: "translateY(-4px)",
        boxShadow: "0 14px 30px rgba(15, 23, 42, 0.08)",
      }}
    >
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
          bg={iconBg}
          alignItems="center"
          justifyContent="center"
          color={iconColor}
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
