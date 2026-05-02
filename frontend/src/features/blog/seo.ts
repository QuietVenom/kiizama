import type { BlogPost } from "./types"

export type BlogSeoAsset = {
  jsonLd: Record<string, unknown>
  title: string
  links: Array<{ href: string; rel: string }>
  meta: Array<
    { name: string; content: string } | { property: string; content: string }
  >
}

const buildOrganization = () => ({
  "@type": "Organization",
  name: "Kiizama",
  url: "https://www.kiizama.com",
})

export const buildBlogIndexSeo = (
  posts: BlogPost[],
  siteUrl: string,
): BlogSeoAsset => {
  const canonicalUrl = `${siteUrl}/blog`
  const title = "Kiizama Journal | Reputation intelligence insights"
  const description =
    "Product thinking, workflow notes, and reputation intelligence perspectives from Kiizama."

  return {
    title,
    meta: [
      { name: "description", content: description },
      { name: "robots", content: "index,follow" },
      { property: "og:title", content: title },
      { property: "og:description", content: description },
      { property: "og:type", content: "website" },
      { property: "og:url", content: canonicalUrl },
    ],
    links: [{ href: canonicalUrl, rel: "canonical" }],
    jsonLd: {
      "@context": "https://schema.org",
      "@type": "CollectionPage",
      name: "Kiizama Journal",
      description,
      url: canonicalUrl,
      isPartOf: siteUrl,
      about: "Reputation intelligence",
      publisher: buildOrganization(),
      hasPart: posts.map((post) => ({
        "@type": "BlogPosting",
        headline: post.seoTitle,
        url: post.canonicalUrl,
        datePublished: post.publishedAt,
      })),
    },
  }
}

export const buildBlogPostSeo = (post: BlogPost): BlogSeoAsset => {
  const articleJsonLd: Record<string, unknown> = {
    "@context": "https://schema.org",
    "@type": "Article",
    headline: post.seoTitle,
    description: post.metaDescription,
    datePublished: post.publishedAt,
    mainEntityOfPage: post.canonicalUrl,
    publisher: buildOrganization(),
  }

  if (post.author) {
    articleJsonLd.author = {
      "@type": "Person",
      name: post.author,
    }
  }

  if (post.ogImage) {
    articleJsonLd.image = [post.ogImage]
  }

  return {
    title: post.seoTitle,
    meta: [
      { name: "description", content: post.metaDescription },
      { name: "robots", content: post.robots },
      { property: "og:title", content: post.ogTitle },
      { property: "og:description", content: post.ogDescription },
      { property: "og:type", content: "article" },
      { property: "og:url", content: post.canonicalUrl },
      ...(post.ogImage
        ? [{ property: "og:image", content: post.ogImage } as const]
        : []),
    ],
    links: [{ href: post.canonicalUrl, rel: "canonical" }],
    jsonLd: articleJsonLd,
  }
}
