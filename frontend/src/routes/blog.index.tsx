import {
  Badge,
  Box,
  Container,
  Heading,
  SimpleGrid,
  Stack,
  Text,
} from "@chakra-ui/react"
import { createFileRoute } from "@tanstack/react-router"
import { useEffect, useRef } from "react"
import BlogPostCard from "@/components/Blog/BlogPostCard"
import Footer from "@/components/Landing/Footer"
import LandingNavbar from "@/components/Landing/Navbar"
import { getAllBlogPosts } from "@/features/blog/content"
import { DEFAULT_SITE_URL, normalizeSiteUrl } from "@/features/blog/parser"
import { buildBlogIndexSeo } from "@/features/blog/seo"
import { fetchPublicFeatureFlag } from "@/hooks/useFeatureFlags"

const WAITING_LIST_FLAG_KEY = "waiting-list"
const siteUrl = normalizeSiteUrl(
  import.meta.env.VITE_SITE_URL || DEFAULT_SITE_URL,
)
const posts = getAllBlogPosts()
const blogIndexSeo = buildBlogIndexSeo(posts, siteUrl)

export const Route = createFileRoute("/blog/")({
  loader: async () => {
    try {
      const featureFlag = await fetchPublicFeatureFlag(WAITING_LIST_FLAG_KEY)
      return {
        isWaitingListEnabled: Boolean(
          featureFlag?.is_public && featureFlag.is_enabled,
        ),
        posts,
      }
    } catch {
      return { isWaitingListEnabled: false, posts }
    }
  },
  head: () => ({
    links: blogIndexSeo.links,
    meta: [{ title: blogIndexSeo.title }, ...blogIndexSeo.meta] as never,
    scripts: [
      {
        type: "application/ld+json",
        children: JSON.stringify(blogIndexSeo.jsonLd),
      } as never,
    ],
  }),
  component: BlogIndexPage,
})

function BlogIndexPage() {
  const { isWaitingListEnabled, posts } = Route.useLoaderData()
  const navbarRef = useRef<HTMLElement | null>(null)

  useEffect(() => {
    window.scrollTo({ top: 0, behavior: "auto" })
  }, [])

  return (
    <Box bg="ui.page" minH="100vh">
      <LandingNavbar
        isWaitingListEnabled={isWaitingListEnabled}
        navbarRef={navbarRef}
      />

      <Box
        as="main"
        position="relative"
        overflow="hidden"
        layerStyle="publicPage"
        pt={{ base: 12, md: 16, lg: 20 }}
        pb={{ base: 20, md: 24, lg: 28 }}
      >
        <Box
          position="absolute"
          top="-20"
          right="-20"
          w={{ base: "60", md: "88" }}
          h={{ base: "60", md: "88" }}
          layerStyle="publicGlowPrimary"
          opacity={0.65}
        />
        <Box
          position="absolute"
          top="18%"
          left="-16"
          w={{ base: "52", md: "72" }}
          h={{ base: "52", md: "72" }}
          layerStyle="publicGlowSecondary"
          opacity={0.7}
        />

        <Container maxW="7xl" position="relative">
          <Stack gap={{ base: 10, md: 14 }}>
            <Stack gap={4} maxW="3xl">
              <Badge
                w="fit-content"
                rounded="full"
                px={4}
                py={1.5}
                borderWidth="1px"
                borderColor="ui.brandBorderSoft"
                bg="ui.brandGlow"
                color="ui.brandText"
                letterSpacing="0.08em"
                fontSize="2xs"
                fontWeight="bold"
                textTransform="uppercase"
              >
                Kiizama Journal
              </Badge>

              <Heading
                size={{ base: "3xl", md: "4xl", lg: "5xl" }}
                textStyle="pageTitle"
                lineHeight={1.05}
                letterSpacing="-0.03em"
                maxW="4xl"
              >
                The latest Kiizama insights
              </Heading>

              <Text
                textStyle="pageBody"
                fontSize={{ base: "md", md: "lg" }}
                maxW="2xl"
              >
                Product thinking, workflow notes, and reputation intelligence
                perspectives from Kiizama.
              </Text>
            </Stack>

            <SimpleGrid columns={{ base: 1, lg: 3 }} gap={6}>
              {posts.map((post) => (
                <BlogPostCard key={post.slug} post={post} />
              ))}
            </SimpleGrid>
          </Stack>
        </Container>
      </Box>

      <Footer isWaitingListEnabled={isWaitingListEnabled} />
    </Box>
  )
}
