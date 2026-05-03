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
import { useTranslation } from "react-i18next"
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
  tone: "info" | "accent" | "brand" | "rose" | "success" | "neutral"
}

const featureToneStyles = {
  info: { bg: "ui.infoSoft", color: "ui.infoText" },
  accent: { bg: "ui.accentSoft", color: "ui.accentText" },
  brand: { bg: "ui.brandSoft", color: "ui.brandText" },
  rose: { bg: "ui.roseSoft", color: "ui.roseText" },
  success: { bg: "ui.successSoft", color: "ui.successText" },
  neutral: { bg: "ui.panelAlt", color: "ui.neutralText" },
} as const

type FeaturesProps = {
  sectionRef: RefObject<HTMLElement | null>
}

const Features = ({ sectionRef }: FeaturesProps) => {
  const { t } = useTranslation("landing")
  const features: Feature[] = [
    {
      icon: BsDatabaseDown,
      title: t("features.items.instagramDataCapture.title"),
      description: t("features.items.instagramDataCapture.description"),
      tone: "info",
    },
    {
      icon: FiClipboard,
      title: t("features.items.aiProfileClassification.title"),
      description: t("features.items.aiProfileClassification.description"),
      tone: "accent",
    },
    {
      icon: FiBarChart2,
      title: t("features.items.performanceReports.title"),
      description: t("features.items.performanceReports.description"),
      tone: "brand",
    },
    {
      icon: MdCampaign,
      title: t("features.items.campaignStrategy.title"),
      description: t("features.items.campaignStrategy.description"),
      tone: "rose",
    },
    {
      icon: GiGrowth,
      title: t("features.items.creatorStrategy.title"),
      description: t("features.items.creatorStrategy.description"),
      tone: "success",
    },
    {
      icon: HiMiniQueueList,
      title: t("features.items.asyncJobsPersistence.title"),
      description: t("features.items.asyncJobsPersistence.description"),
      tone: "neutral",
    },
  ]
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
      <Box position="absolute" inset={0} layerStyle="sectionPattern" />

      <Container maxW="7xl" position="relative">
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
            {t("features.eyebrow")}
            <Box as="span" h="1px" w="8" bg="ui.mainHover" />
          </Text>
          <Heading
            size={{ base: "2xl", md: "3xl", lg: "4xl" }}
            color="ui.text"
            letterSpacing="-0.02em"
            lineHeight={1.15}
            fontFamily="'Plus Jakarta Sans', 'Avenir Next', 'Segoe UI', sans-serif"
          >
            {t("features.title")}
          </Heading>
          <Text color="ui.secondaryText" fontSize={{ base: "md", md: "lg" }}>
            {t("features.description")}
          </Text>
        </Stack>

        <SimpleGrid columns={{ base: 1, md: 2, lg: 3 }} gap={7}>
          {features.map((feature, index) => {
            const toneStyle = featureToneStyles[feature.tone]

            return (
              <Box
                key={feature.title}
                layerStyle="landingCard"
                p={{ base: 6, md: 7 }}
                transition="transform 220ms ease, box-shadow 220ms ease, border-color 220ms ease"
                _hover={{
                  transform: "translateY(-4px)",
                  boxShadow: "ui.cardHover",
                  borderColor: "ui.brandBorderSoft",
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
                  bg={toneStyle.bg}
                  color={toneStyle.color}
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
                  color="ui.text"
                  fontFamily="'Plus Jakarta Sans', 'Avenir Next', 'Segoe UI', sans-serif"
                >
                  {feature.title}
                </Heading>
                <Text color="ui.secondaryText" lineHeight="1.75">
                  {feature.description}
                </Text>
              </Box>
            )
          })}
        </SimpleGrid>
      </Container>
    </Box>
  )
}

export default Features
