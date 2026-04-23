import { createFileRoute, notFound } from "@tanstack/react-router"
import { getBlogPostBySlug } from "@/features/blog/content"
import { buildBlogPostSeo } from "@/features/blog/seo"
import { fetchPublicFeatureFlag } from "@/hooks/useFeatureFlags"
import { BlogPostPage } from "./-components/BlogPostPage"

const WAITING_LIST_FLAG_KEY = "waiting-list"

export const Route = createFileRoute("/blog/$slug")({
  loader: async ({ params }) => {
    const post = getBlogPostBySlug(params.slug)

    if (!post) {
      throw notFound()
    }

    try {
      const featureFlag = await fetchPublicFeatureFlag(WAITING_LIST_FLAG_KEY)
      return {
        isWaitingListEnabled: Boolean(
          featureFlag?.is_public && featureFlag.is_enabled,
        ),
        post,
      }
    } catch {
      return {
        isWaitingListEnabled: false,
        post,
      }
    }
  },
  head: ({ loaderData }) => {
    if (!loaderData) {
      return {}
    }

    const postSeo = buildBlogPostSeo(loaderData.post)

    return {
      links: postSeo.links,
      meta: [{ title: postSeo.title }, ...postSeo.meta] as never,
      scripts: [
        {
          type: "application/ld+json",
          children: JSON.stringify(postSeo.jsonLd),
        } as never,
      ],
    }
  },
  component: BlogPostRoute,
})

function BlogPostRoute() {
  const loaderData = Route.useLoaderData()
  const { isWaitingListEnabled, post } = loaderData
  return (
    <BlogPostPage isWaitingListEnabled={isWaitingListEnabled} post={post} />
  )
}
