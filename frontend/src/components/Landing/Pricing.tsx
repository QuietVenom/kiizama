import {
  Box,
  Button,
  Link as ChakraLink,
  Container,
  Heading,
  HStack,
  Icon,
  SimpleGrid,
  Stack,
  Text,
} from "@chakra-ui/react"
import { keyframes } from "@emotion/react"
import { Link } from "@tanstack/react-router"
import type { RefObject } from "react"
import { FiCheck } from "react-icons/fi"
import { getAppUrl } from "@/utils"

type PricingPlan = {
  name: string
  price: string
  description: string
  features: string[]
  highlighted?: boolean
}

const fadeInUp = keyframes`
  from {
    opacity: 0;
    transform: translateY(18px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
`

const plans: PricingPlan[] = [
  {
    name: "Pilot Access",
    price: "TBD",
    description: "Placeholder plan details for early-stage rollout.",
    features: [
      "Scoped onboarding and setup",
      "Limited workflow volume",
      "Standard report generation access",
      "Email support within 24h",
    ],
  },
  {
    name: "Enterprise",
    price: "TBD",
    description: "Placeholder plan details for custom enterprise deployments.",
    features: [
      "Custom operational limits",
      "Advanced strategy workflows",
      "Integrations and governance controls",
      "Priority support",
      "Dedicated onboarding",
    ],
    highlighted: true,
  },
]

type PricingProps = {
  isWaitingListEnabled: boolean
  sectionRef: RefObject<HTMLElement | null>
}

const Pricing = ({ isWaitingListEnabled, sectionRef }: PricingProps) => {
  const loginUrl = getAppUrl("/login")

  const getPrimaryLabel = (highlighted?: boolean) => {
    if (isWaitingListEnabled) return "Join waiting list"
    return highlighted ? "Request access" : "Create account"
  }

  return (
    // biome-ignore lint/correctness/useUniqueElementIds: section anchor is required for footer navigation links
    <Box
      ref={sectionRef}
      id="plans"
      as="section"
      scrollMarginTop="88px"
      py={{ base: 20, md: 24, lg: 28 }}
      bg="gray.50"
      borderY="1px solid"
      borderColor="gray.200"
    >
      <Container maxW="7xl">
        <Stack textAlign="center" gap={4} mb={16} maxW="3xl" mx="auto">
          <Text
            color="orange.500"
            textTransform="uppercase"
            fontWeight="bold"
            letterSpacing="0.12em"
            fontSize="xs"
            display="inline-flex"
            alignItems="center"
            justifyContent="center"
            gap={3}
          >
            <Box as="span" h="1px" w="8" bg="orange.300" />
            Flexible Plans
            <Box as="span" h="1px" w="8" bg="orange.300" />
          </Text>
          <Heading
            size={{ base: "2xl", md: "3xl", lg: "4xl" }}
            color="gray.900"
            letterSpacing="-0.02em"
            lineHeight={1.15}
            fontFamily="'Plus Jakarta Sans', 'Avenir Next', 'Segoe UI', sans-serif"
          >
            Placeholder pricing while we finalize packaging
          </Heading>
          <Text color="gray.500" fontSize={{ base: "md", md: "lg" }}>
            Final plan structure and billing details will be published after
            pilot validation.
          </Text>
        </Stack>

        <SimpleGrid columns={{ base: 1, lg: 2 }} gap={8}>
          {plans.map((plan, index) => (
            <Box
              key={plan.name}
              position="relative"
              bg={plan.highlighted ? "#18183B" : "white"}
              color={plan.highlighted ? "white" : "gray.900"}
              rounded="3xl"
              p={{ base: 7, md: 8 }}
              borderWidth="1px"
              borderColor={plan.highlighted ? "whiteAlpha.200" : "gray.200"}
              boxShadow={
                plan.highlighted
                  ? "0 28px 56px rgba(24, 24, 59, 0.30)"
                  : "0 12px 28px rgba(15, 23, 42, 0.06)"
              }
              transform={plan.highlighted ? { lg: "scale(1.04)" } : undefined}
              animation={`${fadeInUp} 560ms ease`}
              animationDelay={`${index * 120}ms`}
              animationFillMode="both"
            >
              {plan.highlighted && (
                <Box
                  position="absolute"
                  top="-4"
                  right={{ base: 8, md: 10 }}
                  rounded="full"
                  px={4}
                  py={1.5}
                  bg="linear-gradient(90deg, #FB923C, #F59E0B)"
                  color="white"
                  fontSize="xs"
                  fontWeight="bold"
                  letterSpacing="0.08em"
                  textTransform="uppercase"
                  boxShadow="0 10px 18px rgba(245, 158, 11, 0.28)"
                >
                  Recommended
                </Box>
              )}

              <Heading
                size="lg"
                mb={2}
                fontFamily="'Plus Jakarta Sans', 'Avenir Next', 'Segoe UI', sans-serif"
              >
                {plan.name}
              </Heading>

              <Text
                color={plan.highlighted ? "whiteAlpha.700" : "gray.500"}
                mb={8}
              >
                {plan.description}
              </Text>

              <HStack
                align="baseline"
                gap={2}
                mb={8}
                pb={8}
                borderBottomWidth="1px"
                borderColor={plan.highlighted ? "whiteAlpha.200" : "gray.100"}
              >
                <Text fontSize="5xl" fontWeight="extrabold" lineHeight={1}>
                  {plan.price}
                </Text>
                <Text
                  color={plan.highlighted ? "whiteAlpha.600" : "gray.500"}
                  fontWeight="medium"
                >
                  / placeholder
                </Text>
              </HStack>

              <Stack gap={4} mb={10}>
                {plan.features.map((feature) => (
                  <HStack key={feature} align="flex-start" gap={3}>
                    <Box
                      boxSize="6"
                      rounded="full"
                      bg={plan.highlighted ? "whiteAlpha.200" : "gray.100"}
                      color={plan.highlighted ? "orange.300" : "gray.600"}
                      display="inline-flex"
                      alignItems="center"
                      justifyContent="center"
                      mt="1"
                      flexShrink={0}
                    >
                      <Icon as={FiCheck} boxSize="3.5" />
                    </Box>
                    <Text
                      color={plan.highlighted ? "whiteAlpha.900" : "gray.700"}
                    >
                      {feature}
                    </Text>
                  </HStack>
                ))}
              </Stack>

              <Link to={isWaitingListEnabled ? "/waiting-list" : "/signup"}>
                <Button
                  w="full"
                  h={14}
                  rounded="2xl"
                  bg={
                    plan.highlighted
                      ? "linear-gradient(90deg, #FB923C, #F59E0B)"
                      : "gray.900"
                  }
                  color="white"
                  fontWeight="bold"
                  _hover={{
                    bg: plan.highlighted
                      ? "linear-gradient(90deg, #F97316, #D97706)"
                      : "gray.800",
                    transform: "translateY(-4px) scale(1.02)",
                    boxShadow: plan.highlighted
                      ? "0 18px 32px rgba(245, 158, 11, 0.35)"
                      : "0 16px 28px rgba(15, 23, 42, 0.22)",
                  }}
                  transition="all 220ms ease"
                >
                  {getPrimaryLabel(plan.highlighted)}
                </Button>
              </Link>
            </Box>
          ))}
        </SimpleGrid>

        <Box
          mt={14}
          rounded="3xl"
          borderWidth="1px"
          borderColor="gray.200"
          bg="white"
          p={{ base: 6, md: 8 }}
          textAlign="center"
          boxShadow="sm"
        >
          <Text
            fontSize={{ base: "md", md: "lg" }}
            color="gray.800"
            fontWeight="semibold"
            mb={6}
          >
            Need early access details for your team?
          </Text>
          <HStack justify="center" gap={4} flexWrap="wrap">
            <Link to={isWaitingListEnabled ? "/waiting-list" : "/signup"}>
              <Button
                h={12}
                px={7}
                rounded="xl"
                bg="#F5C58E"
                color="gray.900"
                _hover={{
                  bg: "#EEB576",
                  transform: "translateY(-3px) scale(1.02)",
                  boxShadow: "0 14px 24px rgba(245, 158, 11, 0.24)",
                }}
                transition="all 220ms ease"
              >
                {isWaitingListEnabled ? "Join waiting list" : "Create account"}
              </Button>
            </Link>
            <ChakraLink href={loginUrl} _hover={{ textDecoration: "none" }}>
              <Button
                h={12}
                px={7}
                rounded="xl"
                variant="ghost"
                color="gray.600"
                _hover={{
                  bg: "gray.100",
                  color: "gray.900",
                  transform: "translateY(-2px) scale(1.015)",
                  boxShadow: "0 10px 20px rgba(15, 23, 42, 0.10)",
                }}
                transition="all 220ms ease"
              >
                Log in
              </Button>
            </ChakraLink>
          </HStack>
        </Box>
      </Container>
    </Box>
  )
}

export default Pricing
