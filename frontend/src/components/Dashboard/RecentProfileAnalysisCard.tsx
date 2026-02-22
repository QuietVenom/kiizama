import { Badge, Box, Button, Flex, HStack, Icon, Text } from "@chakra-ui/react"
import { FiChevronRight } from "react-icons/fi"
import { PiInstagramLogo } from "react-icons/pi"

type AnalysisStatus = "Completed" | "Analyzing" | "Queued"

type AnalysisItem = {
  username: string
  category: string
  reputation: number
  status: AnalysisStatus
}

const defaultItems: AnalysisItem[] = [
  {
    username: "@alex_design",
    category: "Lifestyle",
    reputation: 92,
    status: "Completed",
  },
  {
    username: "@tech_insights",
    category: "Technology",
    reputation: 78,
    status: "Analyzing",
  },
  {
    username: "@travel_with_me",
    category: "Travel",
    reputation: 85,
    status: "Completed",
  },
  {
    username: "@fitness_pro",
    category: "Health",
    reputation: 64,
    status: "Queued",
  },
]

const statusStyles: Record<AnalysisStatus, { bg: string; color: string }> = {
  Completed: { bg: "#DCFCE7", color: "#16A34A" },
  Analyzing: { bg: "#DBEAFE", color: "#3B82F6" },
  Queued: { bg: "#E2E8F0", color: "#64748B" },
}

const RecentProfileAnalysisCard = () => {
  return (
    <Box
      bg="white"
      borderWidth="1px"
      borderColor="ui.sidebarBorder"
      rounded="4xl"
      p={{ base: 5, lg: 7 }}
      boxShadow="0 4px 20px rgba(15, 23, 42, 0.04)"
    >
      <Flex
        alignItems={{ base: "flex-start", md: "center" }}
        justifyContent="space-between"
        mb={6}
        gap={4}
        direction={{ base: "column", md: "row" }}
      >
        <HStack gap={3}>
          <Icon as={PiInstagramLogo} color="#EC4899" boxSize={7} />
          <Text
            fontSize={{ base: "lg", lg: "2xl" }}
            fontWeight="black"
            letterSpacing="-0.02em"
          >
            Recent Profile Analysis
          </Text>
        </HStack>
        <Button
          variant="ghost"
          color="#F97316"
          px={2}
          h="auto"
          fontSize={{ base: "sm", lg: "lg" }}
          fontWeight="bold"
          _hover={{ color: "#EA580C", bg: "transparent" }}
        >
          View all
          <Icon as={FiChevronRight} boxSize={5} />
        </Button>
      </Flex>

      <Flex direction="column" gap={2.5}>
        {defaultItems.map((item) => {
          const statusStyle = statusStyles[item.status]

          return (
            <Flex
              key={item.username}
              alignItems="center"
              justifyContent="space-between"
              gap={{ base: 3, lg: 4 }}
              rounded="2xl"
              px={{ base: 3, lg: 4 }}
              py={{ base: 2.5, lg: 3 }}
              transition="background-color 180ms ease, border-color 180ms ease"
              borderWidth="1px"
              borderColor="transparent"
              _hover={{ bg: "ui.surfaceSoft", borderColor: "ui.sidebarBorder" }}
            >
              <HStack gap={4} minW={0}>
                <Box
                  boxSize={{ base: "38px", lg: "44px" }}
                  rounded="full"
                  bg="#E2E8F0"
                />
                <Box minW={0}>
                  <Text
                    fontSize={{ base: "sm", lg: "lg" }}
                    fontWeight="bold"
                    lineHeight="1.1"
                    truncate
                  >
                    {item.username}
                  </Text>
                  <Text
                    fontSize={{ base: "xs", lg: "sm" }}
                    color="ui.mutedText"
                    fontWeight="medium"
                    truncate
                  >
                    {item.category}
                  </Text>
                </Box>
              </HStack>

              <Flex
                alignItems="center"
                gap={{ base: 3, lg: 6 }}
                minW={{ base: "auto", lg: "280px" }}
                justifyContent="flex-end"
              >
                <Box textAlign="center" display={{ base: "none", sm: "block" }}>
                  <Text
                    fontSize={{ base: "10px", lg: "xs" }}
                    color="ui.mutedText"
                    fontWeight="bold"
                    textTransform="uppercase"
                    letterSpacing="0.04em"
                  >
                    Reputation
                  </Text>
                  <Text
                    fontSize={{ base: "sm", lg: "lg" }}
                    fontWeight="bold"
                    color="#059669"
                    lineHeight="1.1"
                  >
                    {item.reputation}%
                  </Text>
                </Box>

                <Badge
                  bg={statusStyle.bg}
                  color={statusStyle.color}
                  px={4}
                  py={1.5}
                  rounded="full"
                  textTransform="uppercase"
                  letterSpacing="0.16em"
                  fontSize="xs"
                  fontWeight="black"
                  whiteSpace="nowrap"
                >
                  {item.status}
                </Badge>
              </Flex>
            </Flex>
          )
        })}
      </Flex>
    </Box>
  )
}

export default RecentProfileAnalysisCard
