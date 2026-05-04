import { Box, Flex, Icon, Link, Text } from "@chakra-ui/react"
import { keyframes } from "@emotion/react"
import { useTranslation } from "react-i18next"
import { FiUser } from "react-icons/fi"
import { IoNewspaperOutline } from "react-icons/io5"
import { getAllBlogPosts } from "@/features/blog/content"

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

const latestBlogPosts = getAllBlogPosts().slice(0, 3)

type StrategicInsightCardProps = {
  planLabel: string
  periodLabel: string
  periodValue: string
}

const StrategicInsightCard = ({
  planLabel,
  periodLabel,
  periodValue,
}: StrategicInsightCardProps) => {
  const { t } = useTranslation("dashboard")
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
                {t("overview.strategic.news")}
              </Text>
            </Flex>
            {latestBlogPosts.length > 0 ? (
              <Flex direction="column" gap={3}>
                {latestBlogPosts.map((post) => (
                  <Link
                    key={post.slug}
                    href={`/blog/${post.slug}`}
                    target="_blank"
                    rel="noreferrer"
                    color="ui.textInverse"
                    fontSize={{ base: "sm", lg: "md" }}
                    fontWeight="semibold"
                    lineHeight="1.4"
                    _hover={{ color: "ui.main", textDecoration: "none" }}
                  >
                    {post.title}
                  </Link>
                ))}
              </Flex>
            ) : (
              <Text
                fontSize={{ base: "sm", lg: "md" }}
                color="ui.inverseMutedText"
              >
                {t("overview.strategic.noPosts")}
              </Text>
            )}
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
            {t("overview.strategic.planStatus")}
          </Text>
        </Flex>
        <Flex direction="column" gap={3}>
          <Text color="ui.secondaryText">
            {t("overview.strategic.planType")}:{" "}
            <Text as="span" fontWeight="bold" color="inherit">
              {planLabel}
            </Text>
          </Text>
          <Text color="ui.secondaryText">
            {periodLabel}:{" "}
            <Text as="span" fontWeight="bold" color="inherit">
              {periodValue}
            </Text>
          </Text>
        </Flex>
      </Box>
    </Flex>
  )
}

export default StrategicInsightCard
