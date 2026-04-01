import type { BlogPost } from "./parser"
import { DEFAULT_SITE_URL, parseBlogPostModules } from "./parser"

const blogModules = import.meta.glob<string>("../../../content/blog/*.md", {
  eager: true,
  import: "default",
  query: "?raw",
})

const blogPosts = parseBlogPostModules(blogModules, {
  siteUrl: import.meta.env.VITE_SITE_URL || DEFAULT_SITE_URL,
})

export const getAllBlogPosts = (): BlogPost[] => blogPosts

export const getBlogPostBySlug = (slug: string): BlogPost | undefined =>
  blogPosts.find((post) => post.slug === slug)
