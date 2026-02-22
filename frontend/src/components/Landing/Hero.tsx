import {
  Badge,
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
import { BsFileEarmarkPersonFill } from "react-icons/bs"
import {
  FiArrowRight,
  FiCheck,
  FiCheckCircle,
  FiChevronRight,
} from "react-icons/fi"
import { TbLayoutList } from "react-icons/tb"
import { getAppUrl } from "@/utils"

const fadeInUp = keyframes`
  from {
    opacity: 0;
    transform: translateY(20px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
`

const pulse = keyframes`
  0% {
    transform: scale(0.85);
    opacity: 0.8;
  }
  75% {
    transform: scale(1.9);
    opacity: 0;
  }
  100% {
    transform: scale(1.9);
    opacity: 0;
  }
`

const trustSignals = [
  "Profile snapshots and engagement metrics",
  "AI-powered classification workflows",
  "Strategic HTML and PDF reports",
  "Durable storage and async pipelines",
]

type HeroProps = {
  isWaitingListEnabled: boolean
  sectionRef: RefObject<HTMLElement | null>
}

const Hero = ({ isWaitingListEnabled, sectionRef }: HeroProps) => {
  const loginUrl = getAppUrl("/login")

  return (
    <Box
      ref={sectionRef}
      as="section"
      position="relative"
      overflow="hidden"
      bgGradient="linear(to-b, #FFFDF8, #FFF9ED 48%, white)"
      minH="100dvh"
      display="flex"
      alignItems="center"
      py={{ base: 20, md: 24, lg: 28 }}
    >
      <Box
        position="absolute"
        top="-32"
        right="-24"
        w={{ base: "72", md: "96" }}
        h={{ base: "72", md: "96" }}
        rounded="full"
        bg="orange.100"
        opacity={0.7}
        filter="blur(110px)"
      />
      <Box
        position="absolute"
        top="24%"
        left="-24"
        w={{ base: "52", md: "72" }}
        h={{ base: "52", md: "72" }}
        rounded="full"
        bg="orange.50"
        opacity={0.85}
        filter="blur(90px)"
      />

      <Container maxW="7xl" position="relative">
        <SimpleGrid
          columns={{ base: 1, lg: 2 }}
          gap={{ base: 12, lg: 14 }}
          alignItems="center"
        >
          <Stack
            gap={7}
            animation={`${fadeInUp} 620ms ease`}
            animationFillMode="both"
          >
            <Badge
              w="fit-content"
              rounded="full"
              px={4}
              py={1.5}
              borderWidth="1px"
              borderColor="orange.200"
              bg="orange.100"
              color="orange.800"
              letterSpacing="0.08em"
              fontSize="2xs"
              fontWeight="bold"
              textTransform="uppercase"
              display="inline-flex"
              alignItems="center"
              gap={2}
            >
              <Box position="relative" boxSize="2">
                <Box
                  position="absolute"
                  inset={0}
                  rounded="full"
                  bg="orange.300"
                  animation={`${pulse} 1.5s ease-out infinite`}
                />
                <Box
                  position="absolute"
                  inset={0}
                  rounded="full"
                  bg="orange.500"
                />
              </Box>
              Instagram Reputation Intelligence
            </Badge>

            <Heading
              fontSize={{ base: "6xl", md: "6xl", lg: "7xl" }}
              lineHeight={1.05}
              letterSpacing="-0.03em"
              color="gray.900"
              fontFamily="'Plus Jakarta Sans', 'Avenir Next', 'Segoe UI', sans-serif"
            >
              Turn Instagram data into{" "}
              <Box
                as="span"
                display="inline"
                style={{
                  color: "transparent",
                  backgroundImage:
                    "linear-gradient(to right, #f97316, #f59e0b)",
                  WebkitBackgroundClip: "text",
                  backgroundClip: "text",
                  WebkitTextFillColor: "transparent",
                }}
              >
                reputation strategy
              </Box>
            </Heading>

            <Text
              fontSize={{ base: "md", md: "xl" }}
              color="gray.600"
              maxW="2xl"
              lineHeight="1.8"
            >
              Built for Public Relations, Marketing, Creators, and Talent teams.
              Analyze profiles, classify with AI, and generate strategic outputs
              in minutes.
            </Text>

            <HStack gap={4} flexWrap="wrap">
              {isWaitingListEnabled ? (
                <Link to="/waiting-list">
                  <Button
                    h={14}
                    px={8}
                    rounded="xl"
                    bg="#F5C58E"
                    color="gray.900"
                    fontWeight="bold"
                    boxShadow="0 16px 34px rgba(245, 197, 142, 0.28)"
                    _hover={{ bg: "#EEB576", transform: "translateY(-2px)" }}
                    transition="all 200ms ease"
                  >
                    Join waiting list
                    <FiArrowRight />
                  </Button>
                </Link>
              ) : (
                <Link to="/signup">
                  <Button
                    h={14}
                    px={8}
                    rounded="xl"
                    bg="#F5C58E"
                    color="gray.900"
                    fontWeight="bold"
                    boxShadow="0 16px 34px rgba(245, 197, 142, 0.28)"
                    _hover={{ bg: "#EEB576", transform: "translateY(-2px)" }}
                    transition="all 200ms ease"
                  >
                    Sign Up
                    <FiArrowRight />
                  </Button>
                </Link>
              )}
              <ChakraLink href={loginUrl} _hover={{ textDecoration: "none" }}>
                <Button
                  variant="ghost"
                  color="gray.600"
                  fontWeight="semibold"
                  _hover={{ bg: "transparent", color: "gray.900" }}
                >
                  I already have an account
                  <FiChevronRight />
                </Button>
              </ChakraLink>
            </HStack>

            <SimpleGrid columns={{ base: 1, md: 2 }} gapX={6} gapY={4}>
              {trustSignals.map((signal) => (
                <HStack key={signal} align="center" gap={3}>
                  <Box
                    boxSize="5"
                    rounded="full"
                    bg="green.100"
                    color="green.600"
                    display="inline-flex"
                    alignItems="center"
                    justifyContent="center"
                    flexShrink={0}
                  >
                    <Icon as={FiCheck} boxSize="3.5" />
                  </Box>
                  <Text color="gray.600" fontSize="sm" fontWeight="medium">
                    {signal}
                  </Text>
                </HStack>
              ))}
            </SimpleGrid>
          </Stack>

          <Box
            h={{ base: "460px", md: "560px", lg: "620px" }}
            position="relative"
            animation={`${fadeInUp} 760ms ease`}
            animationFillMode="both"
          >
            <Box
              position="absolute"
              inset={{ base: 1, md: 6 }}
              rounded="4xl"
              bg="rgba(255, 255, 255, 0.62)"
              borderWidth="1px"
              borderColor="rgba(255, 255, 255, 0.9)"
              boxShadow="0 26px 62px rgba(15, 23, 42, 0.06)"
              transform="rotate(3deg)"
            />
            <Box
              position="absolute"
              inset={{ base: 4, md: 12 }}
              rounded="4xl"
              bg="rgba(245, 197, 142, 0.16)"
              borderWidth="1px"
              borderColor="rgba(245, 197, 142, 0.38)"
              boxShadow="inset 0 0 0 1px rgba(255, 255, 255, 0.5)"
              transform="rotate(-3deg)"
            />

            <Box
              position="absolute"
              top={{ base: "4%", md: "8%" }}
              left={{ base: "0%", md: "-4%" }}
              w={{ base: "86%", md: "66%" }}
              rounded="3xl"
              bg="white"
              borderWidth="1px"
              borderColor="#E8EDF5"
              boxShadow="0 20px 52px rgba(15, 23, 42, 0.10)"
              px={{ base: 5, md: 6 }}
              py={{ base: 5, md: 6 }}
              zIndex={2}
            >
              <HStack gap={4} align="center" pb={5}>
                <Box
                  boxSize={{ base: "14", md: "16" }}
                  rounded="2xl"
                  bg="#FFF7EB"
                  color="#F97316"
                  display="inline-flex"
                  alignItems="center"
                  justifyContent="center"
                  flexShrink={0}
                >
                  <Icon as={BsFileEarmarkPersonFill} boxSize={7} />
                </Box>
                <Text
                  fontWeight="bold"
                  color="#243047"
                  fontSize={{ base: "lg", md: "xl" }}
                  lineHeight={1.2}
                  letterSpacing="-0.02em"
                >
                  Creator Performance
                  <br />
                  Report
                </Text>
              </HStack>
              <Box h="1px" w="full" bg="#EAEFF5" mb={6} />
              <HStack mb={5} gap={4}>
                <Box boxSize="16" rounded="full" bg="#EDF1F7" />
                <Box h="4" w="44%" rounded="full" bg="#E8EDF5" />
              </HStack>
              <Stack gap={4}>
                <Box h="3.5" rounded="full" bg="#E8EDF5" />
                <Box h="3.5" rounded="full" bg="#E8EDF5" w="84%" />
              </Stack>
            </Box>

            <Box
              position="absolute"
              top={{ base: "30%", md: "27%" }}
              right={{ base: "0%", md: "-8%" }}
              w={{ base: "80%", md: "63%" }}
              rounded="3xl"
              bg="white"
              borderWidth="1px"
              borderColor="#E8EDF5"
              boxShadow="0 20px 52px rgba(15, 23, 42, 0.10)"
              px={{ base: 5, md: 6 }}
              py={{ base: 5, md: 6 }}
              zIndex={3}
            >
              <HStack gap={4} align="center" pb={5}>
                <Box
                  boxSize={{ base: "12", md: "14" }}
                  rounded="2xl"
                  bg="#EBF3FF"
                  color="#3B82F6"
                  display="inline-flex"
                  alignItems="center"
                  justifyContent="center"
                  flexShrink={0}
                >
                  <Icon as={TbLayoutList} boxSize={7} />
                </Box>
                <Text
                  fontWeight="bold"
                  color="#243047"
                  fontSize={{ base: "lg", md: "xl" }}
                  lineHeight={1.2}
                  letterSpacing="-0.02em"
                >
                  Brand Reputation
                </Text>
              </HStack>
              <Box h="1px" w="full" bg="#EAEFF5" mb={6} />
              <HStack mb={5} gap={4}>
                <Box
                  h={{ base: "24", md: "28" }}
                  w="56%"
                  rounded="2xl"
                  bg="#F4F7FB"
                  borderWidth="1px"
                  borderColor="#E8EDF5"
                />
                <Box
                  h={{ base: "24", md: "28" }}
                  w="44%"
                  rounded="2xl"
                  bg="#F4F7FB"
                  borderWidth="1px"
                  borderColor="#E8EDF5"
                />
              </HStack>
              <Box h="3.5" rounded="full" bg="#E8EDF5" w="64%" />
            </Box>

            <Box
              position="absolute"
              bottom={{ base: "-10%", md: "-3%" }}
              left={{ base: "2%", md: "10%" }}
              w={{ base: "82%", md: "68%" }}
              rounded="3xl"
              bg="white"
              borderWidth="1px"
              borderColor="#E8EDF5"
              boxShadow="0 26px 58px rgba(15, 23, 42, 0.14)"
              px={{ base: 5, md: 6 }}
              py={{ base: 5, md: 6 }}
              zIndex={4}
            >
              <HStack justify="space-between" align="center" pb={5}>
                <HStack gap={4}>
                  <Box
                    boxSize={{ base: "12", md: "14" }}
                    rounded="2xl"
                    bg="#E8F8EC"
                    color="#22C55E"
                    display="inline-flex"
                    alignItems="center"
                    justifyContent="center"
                    flexShrink={0}
                  >
                    <Icon as={FiCheckCircle} boxSize={7} />
                  </Box>
                  <Text
                    fontWeight="bold"
                    color="#243047"
                    fontSize={{ base: "lg", md: "xl" }}
                    lineHeight={1.2}
                    letterSpacing="-0.02em"
                  >
                    Creator Reputation
                  </Text>
                </HStack>
                <Box
                  rounded="full"
                  px={4}
                  py={2}
                  bg="#D7F3E1"
                  color="#15803D"
                  fontWeight="bold"
                  fontSize={{ base: "2xs", md: "sm" }}
                >
                  High
                </Box>
              </HStack>
              <Box h="1px" w="full" bg="#EAEFF5" mb={6} />
              <Stack gap={4} mb={6}>
                <Box h="3.5" rounded="full" bg="#E8EDF5" />
                <Box h="3.5" rounded="full" bg="#E8EDF5" w="83%" />
                <Box h="3.5" rounded="full" bg="#E8EDF5" w="74%" />
              </Stack>
              <HStack gap={3}>
                <Box
                  h={{ base: "12", md: "14" }}
                  flex={1}
                  rounded="2xl"
                  bg="#FFF7EB"
                  borderWidth="1px"
                  borderColor="#FAD7AE"
                />
                <Box
                  h={{ base: "12", md: "14" }}
                  flex={1}
                  rounded="2xl"
                  bg="#ECEFF5"
                />
                <Box
                  h={{ base: "12", md: "14" }}
                  flex={1}
                  rounded="2xl"
                  bg="#ECEFF5"
                />
              </HStack>
            </Box>
          </Box>
        </SimpleGrid>
      </Container>
    </Box>
  )
}

export default Hero
