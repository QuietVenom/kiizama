export type BlogPostFrontmatter = {
  title: string
  slug: string
  excerpt: string
  publishedAt: string
  author?: string
  coverImage?: string
  tags?: string[]
  draft?: boolean
  seoTitle?: string
  metaDescription?: string
  canonicalUrl?: string
  ogTitle?: string
  ogDescription?: string
  ogImage?: string
  robots?: string
}

export type BlogPost = Omit<
  BlogPostFrontmatter,
  | "seoTitle"
  | "metaDescription"
  | "canonicalUrl"
  | "ogTitle"
  | "ogDescription"
  | "ogImage"
  | "robots"
> & {
  html: string
  readingTime: number
  seoTitle: string
  metaDescription: string
  canonicalUrl: string
  ogTitle: string
  ogDescription: string
  ogImage?: string
  robots: string
}

export type ParseBlogPostOptions = {
  siteUrl?: string
}

export const DEFAULT_SITE_URL = "https://www.kiizama.com"

export const normalizeSiteUrl = (siteUrl: string) => siteUrl.replace(/\/+$/, "")
