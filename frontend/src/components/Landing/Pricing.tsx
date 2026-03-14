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
  const loginUrl = "/login"

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
      layerStyle="sectionMuted"
    >
      <Container maxW="7xl">
        <Stack textAlign="center" gap={4} mb={16} maxW="3xl" mx="auto">
          <Text
            color="ui.link"
            textTransform="uppercase"
            fontWeight="bold"
            letterSpacing="0.12em"
            fontSize="xs"
            display="inline-flex"
            alignItems="center"
            justifyContent="center"
            gap={3}
          >
            <Box as="span" h="1px" w="8" bg="ui.mainHover" />
            Flexible Plans
            <Box as="span" h="1px" w="8" bg="ui.mainHover" />
          </Text>
          <Heading
            size={{ base: "2xl", md: "3xl", lg: "4xl" }}
            color="ui.text"
            letterSpacing="-0.02em"
            lineHeight={1.15}
            fontFamily="'Plus Jakarta Sans', 'Avenir Next', 'Segoe UI', sans-serif"
          >
            Placeholder pricing while we finalize packaging
          </Heading>
          <Text color="ui.secondaryText" fontSize={{ base: "md", md: "lg" }}>
            Final plan structure and billing details will be published after
            pilot validation.
          </Text>
        </Stack>

        <SimpleGrid columns={{ base: 1, lg: 2 }} gap={8}>
          {plans.map((plan, index) => (
            <Box
              key={plan.name}
              position="relative"
              layerStyle={
                plan.highlighted ? "pricingCardHighlight" : "pricingCard"
              }
              p={{ base: 7, md: 8 }}
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
                  layerStyle="brandGradientBadge"
                  rounded="full"
                  px={4}
                  py={1.5}
                  fontSize="xs"
                  fontWeight="bold"
                  letterSpacing="0.08em"
                  textTransform="uppercase"
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
                color={
                  plan.highlighted ? "ui.inverseMutedText" : "ui.secondaryText"
                }
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
                borderColor={
                  plan.highlighted ? "ui.borderInverse" : "ui.borderSoft"
                }
              >
                <Text fontSize="5xl" fontWeight="extrabold" lineHeight={1}>
                  {plan.price}
                </Text>
                <Text
                  color={
                    plan.highlighted
                      ? "ui.inverseMutedText"
                      : "ui.secondaryText"
                  }
                  fontWeight="medium"
                >
                  / placeholder
                </Text>
              </HStack>

              <Stack gap={4} mb={10}>
                {plan.features.map((feature) => (
                  <HStack key={feature} align="center" gap={3}>
                    <Box
                      boxSize="6"
                      rounded="full"
                      bg={plan.highlighted ? "ui.inverseSoft" : "ui.panelAlt"}
                      color={plan.highlighted ? "ui.main" : "ui.neutralText"}
                      display="inline-flex"
                      alignItems="center"
                      justifyContent="center"
                      flexShrink={0}
                    >
                      <Icon as={FiCheck} boxSize="3.5" />
                    </Box>
                    <Text
                      color={
                        plan.highlighted ? "ui.textInverse" : "ui.secondaryText"
                      }
                      fontWeight="bold"
                      lineHeight="1.35"
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
                  layerStyle={
                    plan.highlighted ? "brandGradientButton" : undefined
                  }
                  bg={plan.highlighted ? undefined : "ui.text"}
                  color="ui.panel"
                  fontWeight="bold"
                  _hover={
                    plan.highlighted
                      ? undefined
                      : {
                          bg: "ui.panelInverse",
                          transform: "translateY(-4px) scale(1.02)",
                          boxShadow: "ui.subtleButton",
                        }
                  }
                  transition={plan.highlighted ? undefined : "all 220ms ease"}
                >
                  {getPrimaryLabel(plan.highlighted)}
                </Button>
              </Link>
            </Box>
          ))}
        </SimpleGrid>

        <Box
          mt={14}
          layerStyle="landingCard"
          p={{ base: 6, md: 8 }}
          textAlign="center"
        >
          <Text
            fontSize={{ base: "md", md: "lg" }}
            color="ui.text"
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
                layerStyle="brandGradientButton"
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
                color="ui.secondaryText"
                _hover={{
                  bg: "ui.panelAlt",
                  color: "ui.text",
                  transform: "translateY(-2px) scale(1.015)",
                  boxShadow: "ui.subtleButton",
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
