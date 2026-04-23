import { screen } from "@testing-library/react"
import type { ReactNode } from "react"
import { describe, expect, test, vi } from "vitest"

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

const BlogPostCard = (await import("../../../src/components/Blog/BlogPostCard"))
  .default

const createPost = (overrides: Partial<BlogPost> = {}): BlogPost => ({
  canonicalUrl: "https://kiizama.test/blog/alpha",
  excerpt: "A concise overview of reputation intelligence.",
  html: "<p>Post content</p>",
  metaDescription: "Meta description",
  ogDescription: "OG description",
  ogTitle: "OG title",
  publishedAt: "2026-04-25T12:00:00Z",
  readingTime: 4,
  robots: "index,follow",
  seoTitle: "SEO title",
  slug: "alpha",
  tags: ["Strategy", "Creators"],
  title: "Alpha post",
  ...overrides,
})

describe("blog post card", () => {
  test("blog_post_card_with_tags_renders_summary_metadata_and_link", () => {
    // Arrange / Act
    renderWithProviders(<BlogPostCard post={createPost()} />)

    // Assert
    expect(screen.getByRole("heading", { name: "Alpha post" })).toBeVisible()
    expect(
      screen.getByText("A concise overview of reputation intelligence."),
    ).toBeVisible()
    expect(screen.getByText("April 25, 2026")).toBeVisible()
    expect(screen.getByText("4 min read")).toBeVisible()
    expect(screen.getByText("Strategy")).toBeVisible()
    expect(screen.getByText("Creators")).toBeVisible()
    expect(screen.getByRole("link", { name: "Read More" })).toHaveAttribute(
      "href",
      "/blog/alpha",
    )
  })

  test("blog_post_card_without_tags_omits_tag_badges", () => {
    // Arrange / Act
    renderWithProviders(<BlogPostCard post={createPost({ tags: [] })} />)

    // Assert
    expect(screen.getByRole("heading", { name: "Alpha post" })).toBeVisible()
    expect(screen.queryByText("Strategy")).not.toBeInTheDocument()
    expect(screen.queryByText("Creators")).not.toBeInTheDocument()
  })
})
