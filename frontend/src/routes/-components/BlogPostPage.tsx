import {
  Badge,
  Box,
  Container,
  Heading,
  HStack,
  Stack,
  Text,
} from "@chakra-ui/react"
import { Link } from "@tanstack/react-router"
import { useEffect, useRef } from "react"
import { useTranslation } from "react-i18next"
import BlogPostContent from "@/components/Blog/BlogPostContent"
import Footer from "@/components/Landing/Footer"
import LandingNavbar from "@/components/Landing/Navbar"
import { formatBlogPublishedAt } from "@/features/blog/format"
import type { BlogPost } from "@/features/blog/types"

type BlogPostPageProps = {
  isWaitingListEnabled: boolean
  post: BlogPost
}

export function BlogPostPage({
  isWaitingListEnabled,
  post,
}: BlogPostPageProps) {
  const { i18n, t } = useTranslation("landing")
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

        <Container maxW="4xl" position="relative">
          <Stack gap={8}>
            <Stack gap={5}>
              <Link to="/blog">
                <Text
                  color="ui.link"
                  fontWeight="bold"
                  w="fit-content"
                  _hover={{ color: "ui.mainHover" }}
                >
                  {t("blog.backToBlog")}
                </Text>
              </Link>

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
                {t("blog.journal")}
              </Badge>

              <Heading
                size={{ base: "3xl", md: "4xl", lg: "5xl" }}
                textStyle="pageTitle"
                lineHeight={1.05}
                letterSpacing="-0.03em"
              >
                {post.title}
              </Heading>

              <HStack wrap="wrap" gap={3} color="ui.secondaryText">
                <Text>
                  {formatBlogPublishedAt(
                    post.publishedAt,
                    i18n.resolvedLanguage ?? i18n.language,
                  )}
                </Text>
                <Text>•</Text>
                <Text>
                  {t("blog.readingTime", { count: post.readingTime })}
                </Text>
                {post.author ? (
                  <>
                    <Text>•</Text>
                    <Text>{post.author}</Text>
                  </>
                ) : null}
              </HStack>

              {post.tags?.length ? (
                <HStack wrap="wrap" gap={2}>
                  {post.tags.map((tag: string) => (
                    <Badge
                      key={tag}
                      rounded="full"
                      px={3}
                      py={1}
                      bg="ui.brandSoft"
                      color="ui.brandText"
                      borderWidth="1px"
                      borderColor="ui.brandBorderSoft"
                    >
                      {tag}
                    </Badge>
                  ))}
                </HStack>
              ) : null}

              <Text textStyle="pageBody" fontSize={{ base: "md", md: "lg" }}>
                {post.excerpt}
              </Text>
            </Stack>

            <Box layerStyle="landingCard" p={{ base: 6, md: 8 }}>
              <BlogPostContent html={post.html} />
            </Box>
          </Stack>
        </Container>
      </Box>

      <Footer isWaitingListEnabled={isWaitingListEnabled} />
    </Box>
  )
}
