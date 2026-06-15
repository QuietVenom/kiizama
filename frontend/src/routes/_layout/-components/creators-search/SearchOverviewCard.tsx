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
    <Box layerStyle="dashboardCard" px={5} py={4}>
      <Flex alignItems="center" justifyContent="space-between" gap={4}>
        <Flex alignItems="center" gap={3} minW={0}>
          <Flex
            boxSize="9"
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
              boxSize={4}
            />
          </Flex>
          <Text color={toneStyle.labelColor} fontSize="sm" fontWeight="bold">
            {label}
          </Text>
        </Flex>

        <Text
          flexShrink={0}
          textAlign="right"
          color="ui.text"
          fontSize={{ base: "2xl", lg: "3xl" }}
          fontWeight="black"
          lineHeight="1"
        >
          {value}
        </Text>
      </Flex>
    </Box>
  )
}
