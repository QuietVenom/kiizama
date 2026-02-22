import { Box, Button, Flex, Icon, Text } from "@chakra-ui/react"
import { FiTrendingUp } from "react-icons/fi"

const StrategicInsightCard = () => {
  return (
    <Box
      bg="ui.footer"
      color="white"
      rounded="4xl"
      p={{ base: 5, lg: 7 }}
      position="relative"
      overflow="hidden"
      minH={{ base: "auto", lg: "100%" }}
      boxShadow="0 14px 34px rgba(24, 24, 59, 0.18)"
    >
      <Box
        position="absolute"
        top="-60px"
        right="-60px"
        boxSize="180px"
        rounded="full"
        bg="rgba(249, 115, 22, 0.22)"
        filter="blur(30px)"
      />

      <Flex direction="column" position="relative" zIndex={1} h="full">
        <Flex
          boxSize="64px"
          rounded="2xl"
          bg="rgba(255,255,255,0.08)"
          borderWidth="1px"
          borderColor="rgba(255,255,255,0.16)"
          alignItems="center"
          justifyContent="center"
          mb={8}
        >
          <Icon as={FiTrendingUp} color="orange.400" boxSize={7} />
        </Flex>

        <Text
          fontSize={{ base: "2xl", lg: "3xl" }}
          fontWeight="black"
          lineHeight="1.1"
          letterSpacing="-0.02em"
          mb={4}
        >
          Strategic Insight
        </Text>

        <Text
          fontSize={{ base: "sm", lg: "md" }}
          color="rgba(226,232,240,0.95)"
          lineHeight="1.6"
          mb={6}
          maxW="26ch"
        >
          Your creator network has grown by 12% this week. We recommend
          generating a "Performance Comparison" report for your Lifestyle tier.
        </Text>

        <Box
          rounded="2xl"
          borderWidth="1px"
          borderColor="rgba(255,255,255,0.1)"
          bg="rgba(255,255,255,0.06)"
          p={4}
          mb={6}
        >
          <Text
            fontSize={{ base: "xs", lg: "sm" }}
            color="orange.300"
            letterSpacing="0.14em"
            textTransform="uppercase"
            fontWeight="bold"
            mb={2}
          >
            Top Performing Role
          </Text>
          <Text fontSize={{ base: "md", lg: "lg" }} fontWeight="bold">
            Creative Director (94%)
          </Text>
        </Box>

        <Button
          mt="auto"
          h="52px"
          rounded="2xl"
          bg="#F97316"
          color="white"
          fontWeight="bold"
          fontSize={{ base: "sm", lg: "md" }}
          _hover={{ bg: "#EA580C", transform: "translateY(-2px) scale(1.01)" }}
          transition="all 200ms ease"
        >
          Generate Report
        </Button>
      </Flex>
    </Box>
  )
}

export default StrategicInsightCard
