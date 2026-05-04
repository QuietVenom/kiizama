import {
  Badge,
  Box,
  Button,
  Heading,
  HStack,
  Stack,
  Text,
} from "@chakra-ui/react"
import { Link } from "@tanstack/react-router"
import { useTranslation } from "react-i18next"
import { formatBlogPublishedAt } from "@/features/blog/format"
import type { BlogPost } from "@/features/blog/types"

type BlogPostCardProps = {
  post: BlogPost
}

const BlogPostCard = ({ post }: BlogPostCardProps) => {
  const { i18n, t } = useTranslation("landing")

  return (
    <Box
      layerStyle="landingCard"
      minH={{ base: "auto", lg: "27rem" }}
      p={{ base: 5, md: 6 }}
      display="flex"
      flexDirection="column"
      justifyContent="space-between"
      transition="transform 220ms ease, box-shadow 220ms ease, border-color 220ms ease"
      _hover={{
        transform: "translateY(-4px)",
        boxShadow: "ui.cardHover",
        borderColor: "ui.brandBorderSoft",
      }}
      data-testid={`blog-card-${post.slug}`}
    >
      <Stack gap={5} flex="1">
        <Stack gap={3}>
          <HStack justify="space-between" align="flex-start" gap={4}>
            <Text
              color="ui.secondaryText"
              fontSize={{ base: "sm", md: "md" }}
              fontWeight="medium"
            >
              {formatBlogPublishedAt(
                post.publishedAt,
                i18n.resolvedLanguage ?? i18n.language,
              )}
            </Text>

            <Text color="ui.secondaryText" fontSize="sm">
              {t("blog.readingTime", { count: post.readingTime })}
            </Text>
          </HStack>

          <Heading
            size={{ base: "lg", md: "xl" }}
            textStyle="pageTitle"
            lineHeight={1.15}
          >
            {post.title}
          </Heading>

          <Text textStyle="pageBody" fontSize={{ base: "md", md: "lg" }}>
            {post.excerpt}
          </Text>
        </Stack>

        {post.tags?.length ? (
          <HStack wrap="wrap" gap={2}>
            {post.tags.map((tag) => (
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
      </Stack>

      <Link to="/blog/$slug" params={{ slug: post.slug }}>
        <Button
          mt={8}
          size="lg"
          rounded="xl"
          bg="ui.panelAlt"
          color="ui.secondaryText"
          borderWidth="1px"
          borderColor="ui.borderSoft"
          _hover={{ color: "ui.text", borderColor: "ui.brandBorderSoft" }}
        >
          {t("blog.readMore")}
        </Button>
      </Link>
    </Box>
  )
}

export default BlogPostCard
