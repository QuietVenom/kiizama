import { Box, Flex, Icon, Text } from "@chakra-ui/react"
import { keyframes } from "@emotion/react"
import { FiUser } from "react-icons/fi"
import { IoNewspaperOutline } from "react-icons/io5"

const newsCardAttention = keyframes`
  0%, 70%, 100% {
    transform: scale(1);
  }
  20% {
    transform: scale(1.01);
  }
  35% {
    transform: scale(1);
  }
`

const StrategicInsightCard = () => {
  return (
    <Flex direction="column" gap={6} h="full" minH="full">
      <Box
        flex={1}
        layerStyle="inverseCard"
        p={{ base: 5, lg: 7 }}
        position="relative"
        overflow="hidden"
        transformOrigin="center"
        willChange="transform"
        animation={`${newsCardAttention} 3.2s ease-in-out infinite`}
      >
        <Box
          position="absolute"
          top="-60px"
          right="-60px"
          boxSize="180px"
          rounded="full"
          bg="ui.brandText"
          opacity={0.22}
          filter="blur(30px)"
        />

        <Flex direction="column" position="relative" zIndex={1} h="full">
          <Box
            rounded="2xl"
            borderWidth="1px"
            borderColor="ui.inverseBorderSoft"
            bg="ui.inverseSoft"
            h="full"
            p={4}
          >
            <Flex alignItems="center" gap={2} mb={3}>
              <Icon as={IoNewspaperOutline} color="ui.main" boxSize={4} />
              <Text
                fontSize={{ base: "xs", lg: "sm" }}
                color="ui.main"
                letterSpacing="0.14em"
                textTransform="uppercase"
                fontWeight="bold"
              >
                News
              </Text>
            </Flex>
            <Text fontSize={{ base: "sm", lg: "md" }}>
              Proximamente integraremos reportes y analisis de audiencias de
              TikTok directamente en Kiizama.
            </Text>
          </Box>
        </Flex>
      </Box>

      <Box
        flex={1}
        display="flex"
        flexDirection="column"
        justifyContent="center"
        layerStyle="dashboardCard"
        p={{ base: 5, lg: 7 }}
      >
        <Flex alignItems="center" gap={2} mb={4}>
          <Icon as={FiUser} boxSize={{ base: 5, lg: 6 }} />
          <Text
            fontSize={{ base: "xl", lg: "2xl" }}
            fontWeight="black"
            letterSpacing="-0.02em"
          >
            Plan Status
          </Text>
        </Flex>
        <Flex direction="column" gap={3}>
          <Text color="ui.secondaryText">
            Plan Type:{" "}
            <Text as="span" fontWeight="bold" color="inherit">
              Base
            </Text>
          </Text>
          <Text color="ui.secondaryText">
            Renewal Day:{" "}
            <Text as="span" fontWeight="bold" color="inherit">
              04 de abril de 2026
            </Text>
          </Text>
        </Flex>
      </Box>
    </Flex>
  )
}

export default StrategicInsightCard
