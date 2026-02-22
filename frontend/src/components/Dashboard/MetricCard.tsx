import { Box, Flex, Icon, Text } from "@chakra-ui/react"
import type { IconType } from "react-icons/lib"

type MetricCardProps = {
  icon: IconType
  label: string
  value: string
  trend: string
  iconBg: string
  iconColor: string
}

const MetricCard = ({
  icon,
  label,
  value,
  trend,
  iconBg,
  iconColor,
}: MetricCardProps) => {
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
      <Flex alignItems="center" justifyContent="space-between" mb={5}>
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
          px={4}
          py={1.5}
          rounded="full"
          bg="ui.surfaceSoft"
          color="ui.secondaryText"
          fontSize="sm"
          lineHeight="1"
          fontWeight="bold"
        >
          {trend}
        </Text>
      </Flex>

      <Text
        fontSize={{ base: "md", lg: "lg" }}
        color="ui.secondaryText"
        textTransform="uppercase"
        letterSpacing="0.06em"
        fontWeight="bold"
        maxW="20ch"
      >
        {label}
      </Text>
      <Text mt={2} fontSize={{ base: "2xl", lg: "3xl" }} fontWeight="black">
        {value}
      </Text>
    </Box>
  )
}

export default MetricCard
