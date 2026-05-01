import { Box, Flex, Icon, Text } from "@chakra-ui/react"
import { FiAlertCircle, FiClock, FiTarget, FiUsers } from "react-icons/fi"

import {
  type OverviewCardTone,
  overviewToneStyles,
} from "./creators-search.logic"

export const SearchOverviewCard = ({
  label,
  tone,
  value,
}: {
  label: string
  tone: OverviewCardTone
  value: string
}) => {
  const toneStyle = overviewToneStyles[tone]

  return (
    <Box layerStyle="dashboardCard" px={5} py={5}>
      <Flex
        alignItems="flex-start"
        justifyContent="space-between"
        gap={4}
        direction="column"
      >
        <Flex alignItems="center" gap={3} minW={0}>
          <Flex
            boxSize="11"
            flexShrink={0}
            alignItems="center"
            justifyContent="center"
            rounded="2xl"
            bg={toneStyle.bg}
            color={toneStyle.color}
          >
            <Icon
              as={
                tone === "danger"
                  ? FiAlertCircle
                  : tone === "warning"
                    ? FiClock
                    : tone === "success"
                      ? FiUsers
                      : FiTarget
              }
              boxSize={5}
            />
          </Flex>
          <Text color={toneStyle.labelColor} fontSize="sm" fontWeight="bold">
            {label}
          </Text>
        </Flex>

        <Text
          w="full"
          textAlign="center"
          fontSize={{ base: "3xl", lg: "4xl" }}
          fontWeight="black"
          lineHeight="1"
        >
          {value}
        </Text>
      </Flex>
    </Box>
  )
}
