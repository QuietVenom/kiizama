import {
  Box,
  Container,
  Heading,
  Icon,
  SimpleGrid,
  Stack,
  Text,
} from "@chakra-ui/react"
import { keyframes } from "@emotion/react"
import type { RefObject } from "react"
import type { IconType } from "react-icons"
import { BsDatabaseDown } from "react-icons/bs"
import { FiBarChart2, FiClipboard } from "react-icons/fi"
import { GiGrowth } from "react-icons/gi"
import { HiMiniQueueList } from "react-icons/hi2"
import { MdCampaign } from "react-icons/md"

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

type Feature = {
  icon: IconType
  title: string
  description: string
  iconBg: string
  iconColor: string
}

const features: Feature[] = [
  {
    icon: BsDatabaseDown,
    title: "Instagram Data Capture",
    description:
      "Collect profile snapshots, posts, reels, and key engagement fields seamlessly in one automated workflow.",
    iconBg: "blue.50",
    iconColor: "blue.500",
  },
  {
    icon: FiClipboard,
    title: "AI Profile Classification",
    description:
      "Classify creators by nuanced categories and roles to accelerate shortlist quality and targeting precision.",
    iconBg: "purple.50",
    iconColor: "purple.500",
  },
  {
    icon: FiBarChart2,
    title: "Performance Reports",
    description:
      "Generate downloadable HTML and PDF outputs from stored Instagram snapshots and historical metrics.",
    iconBg: "orange.50",
    iconColor: "orange.500",
  },
  {
    icon: MdCampaign,
    title: "Campaign Strategy",
    description:
      "Build brand-level strategy inputs leveraging audience demographics, goals, and custom creator sets.",
    iconBg: "pink.50",
    iconColor: "pink.500",
  },
  {
    icon: GiGrowth,
    title: "Creator Strategy",
    description:
      "Generate creator-specific strategy outputs grounded on profile context, performance, and reputation signals.",
    iconBg: "green.50",
    iconColor: "green.500",
  },
  {
    icon: HiMiniQueueList,
    title: "Async Jobs & Persistence",
    description:
      "Run heavy scrape jobs with status tracking, retries, and durable storage across profile collections.",
    iconBg: "gray.100",
    iconColor: "gray.700",
  },
]

type FeaturesProps = {
  sectionRef: RefObject<HTMLElement | null>
}

const Features = ({ sectionRef }: FeaturesProps) => {
  return (
    // biome-ignore lint/correctness/useUniqueElementIds: section anchor is required for footer navigation links
    <Box
      ref={sectionRef}
      id="capabilities"
      as="section"
      position="relative"
      scrollMarginTop="88px"
      py={{ base: 20, md: 24, lg: 28 }}
      overflow="hidden"
    >
      <Box
        position="absolute"
        inset={0}
        bgImage="radial-gradient(circle, rgba(148, 163, 184, 0.22) 1px, transparent 1px)"
        bgSize="24px 24px"
        opacity={0.5}
        pointerEvents="none"
      />

      <Container maxW="7xl" position="relative">
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
            Core Capabilities
            <Box as="span" h="1px" w="8" bg="orange.300" />
          </Text>
          <Heading
            size={{ base: "2xl", md: "3xl", lg: "4xl" }}
            color="gray.900"
            letterSpacing="-0.02em"
            lineHeight={1.15}
            fontFamily="'Plus Jakarta Sans', 'Avenir Next', 'Segoe UI', sans-serif"
          >
            Workflows designed for intelligence at scale
          </Heading>
          <Text color="gray.500" fontSize={{ base: "md", md: "lg" }}>
            Designed for teams that need operational social data, AI enrichment,
            and strategy-ready outputs in one unified platform.
          </Text>
        </Stack>

        <SimpleGrid columns={{ base: 1, md: 2, lg: 3 }} gap={7}>
          {features.map((feature, index) => (
            <Box
              key={feature.title}
              bg="white"
              borderWidth="1px"
              borderColor="gray.100"
              rounded="3xl"
              p={{ base: 6, md: 7 }}
              boxShadow="sm"
              transition="transform 220ms ease, box-shadow 220ms ease, border-color 220ms ease"
              _hover={{
                transform: "translateY(-4px)",
                boxShadow: "lg",
                borderColor: "orange.100",
                "& [data-feature-icon]": {
                  transform: "scale(1.08) rotate(-4deg)",
                },
              }}
              animation={`${fadeInUp} 560ms ease`}
              animationDelay={`${index * 90}ms`}
              animationFillMode="both"
            >
              <Box
                data-feature-icon="true"
                h={14}
                w={14}
                rounded="2xl"
                bg={feature.iconBg}
                color={feature.iconColor}
                display="inline-flex"
                alignItems="center"
                justifyContent="center"
                mb={6}
                transition="transform 220ms ease"
                transformOrigin="center"
              >
                <Icon as={feature.icon} boxSize={6} />
              </Box>

              <Heading
                size="md"
                mb={3}
                color="gray.900"
                fontFamily="'Plus Jakarta Sans', 'Avenir Next', 'Segoe UI', sans-serif"
              >
                {feature.title}
              </Heading>
              <Text color="gray.500" lineHeight="1.75">
                {feature.description}
              </Text>
            </Box>
          ))}
        </SimpleGrid>
      </Container>
    </Box>
  )
}

export default Features
