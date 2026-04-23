import { blogPosts } from "./posts.generated"
import type { BlogPost } from "./types"

export const getAllBlogPosts = (): BlogPost[] => blogPosts

export const getBlogPostBySlug = (slug: string): BlogPost | undefined =>
  blogPosts.find((post) => post.slug === slug)
