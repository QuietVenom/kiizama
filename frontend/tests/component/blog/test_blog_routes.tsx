import { screen } from "@testing-library/react"
import type { ReactNode } from "react"
import { beforeEach, describe, expect, test, vi } from "vitest"

import { getBlogPostBySlug } from "../../../src/features/blog/content"
import type { BlogPost } from "../../../src/features/blog/types"
import { renderWithProviders } from "../helpers/render"

vi.mock("@tanstack/react-router", () => ({
  Link: ({
    children,
    params,
    to,
  }: {
    children: ReactNode
    params?: { slug?: string }
    to: string
  }) => <a href={to.replace("$slug", params?.slug ?? "")}>{children}</a>,
}))

vi.mock("@/components/Landing/Navbar", () => ({
  default: ({ isWaitingListEnabled }: { isWaitingListEnabled: boolean }) => (
    <nav>{isWaitingListEnabled ? "Waiting list enabled" : "Navbar"}</nav>
  ),
}))

vi.mock("@/components/Landing/Footer", () => ({
  default: ({ isWaitingListEnabled }: { isWaitingListEnabled: boolean }) => (
    <footer>{isWaitingListEnabled ? "Footer waiting list" : "Footer"}</footer>
  ),
}))

const { BlogIndexPage } = await import(
  "../../../src/routes/-components/BlogIndexPage"
)
const { BlogPostPage } = await import(
  "../../../src/routes/-components/BlogPostPage"
)

const createPost = (overrides: Partial<BlogPost> = {}): BlogPost => ({
  author: "Kiizama",
  canonicalUrl: "https://kiizama.test/blog/alpha",
  excerpt: "Alpha excerpt",
  html: "<p>Alpha body</p>",
  metaDescription: "Meta description",
  ogDescription: "OG description",
  ogTitle: "OG title",
  publishedAt: "2026-04-25T12:00:00Z",
  readingTime: 3,
  robots: "index,follow",
  seoTitle: "SEO title",
  slug: "alpha",
  tags: ["Strategy"],
  title: "Alpha post",
  ...overrides,
})

describe("blog route presentation", () => {
  beforeEach(() => {
    window.scrollTo = vi.fn()
  })

  test("blog_index_route_renders_supplied_posts_and_waiting_list_state", () => {
    // Arrange
    const posts = [
      createPost(),
      createPost({ slug: "beta", tags: [], title: "Beta post" }),
    ]

    // Act
    renderWithProviders(
      <BlogIndexPage isWaitingListEnabled={true} posts={posts} />,
      { language: "en" },
    )

    // Assert
    expect(
      screen.getByRole("heading", { name: "The latest Kiizama insights" }),
    ).toBeVisible()
    expect(screen.getByText("Kiizama Journal")).toBeVisible()
    expect(
      screen.getByText(
        "Product thinking, workflow notes, and reputation intelligence perspectives from Kiizama.",
      ),
    ).toBeVisible()
    expect(screen.getByRole("heading", { name: "Alpha post" })).toBeVisible()
    expect(screen.getByRole("heading", { name: "Beta post" })).toBeVisible()
    expect(screen.getByText("Waiting list enabled")).toBeVisible()
  })

  test("blog_detail_route_renders_post_metadata_and_content", () => {
    // Arrange
    const post = createPost()

    // Act
    renderWithProviders(
      <BlogPostPage isWaitingListEnabled={false} post={post} />,
      { language: "en" },
    )

    // Assert
    expect(screen.getByRole("link", { name: "Back to Blog" })).toHaveAttribute(
      "href",
      "/blog",
    )
    expect(screen.getByRole("heading", { name: "Alpha post" })).toBeVisible()
    expect(screen.getByText("Kiizama Journal")).toBeVisible()
    expect(screen.getByText("April 25, 2026")).toBeVisible()
    expect(screen.getByText("3 min read")).toBeVisible()
    expect(screen.getByText("Kiizama")).toBeVisible()
    expect(screen.getByText("Alpha body")).toBeVisible()
  })

  test("blog_detail_route_uses_translated_public_blog_labels", () => {
    const post = createPost({ publishedAt: "2026-04-05", readingTime: 1 })

    renderWithProviders(
      <BlogPostPage isWaitingListEnabled={false} post={post} />,
      { language: "es" },
    )

    expect(
      screen.getByRole("link", { name: "Volver al blog" }),
    ).toHaveAttribute("href", "/blog")
    expect(screen.getByText("Journal de Kiizama")).toBeVisible()
    expect(screen.getByText("5 de abril de 2026")).toBeVisible()
    expect(screen.getByText("1 min de lectura")).toBeVisible()
  })

  test("blog_detail_unknown_slug_is_not_found_by_content_lookup", () => {
    // Arrange / Act
    const post = getBlogPostBySlug("does-not-exist")

    // Assert
    expect(post).toBeUndefined()
  })
})
