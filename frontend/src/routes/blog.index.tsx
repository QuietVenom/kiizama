import { createFileRoute } from "@tanstack/react-router"
import { getAllBlogPosts } from "@/features/blog/content"
import { buildBlogIndexSeo } from "@/features/blog/seo"
import { DEFAULT_SITE_URL, normalizeSiteUrl } from "@/features/blog/types"
import { fetchPublicFeatureFlag } from "@/hooks/useFeatureFlags"
import { BlogIndexPage } from "./-components/BlogIndexPage"

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
  component: BlogIndexRoute,
})

function BlogIndexRoute() {
  const { isWaitingListEnabled, posts } = Route.useLoaderData()
  return (
    <BlogIndexPage isWaitingListEnabled={isWaitingListEnabled} posts={posts} />
  )
}
