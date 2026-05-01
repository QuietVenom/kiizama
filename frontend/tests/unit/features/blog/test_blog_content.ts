import { describe, expect, test } from "vitest"

import {
  parseBlogPostModule,
  parseBlogPostModules,
} from "../../../../src/features/blog/parser"
import { buildBlogPostSeo } from "../../../../src/features/blog/seo"

const createMarkdown = (
  frontmatter: string,
  body = "Hello world from Kiizama.",
) => `---\n${frontmatter}\n---\n\n${body}\n`

describe("blog content parsing", () => {
  test("blog_content_valid_posts_sorts_by_published_at_descending", () => {
    // Arrange / Act
    const posts = parseBlogPostModules({
      "/content/blog/older.md": createMarkdown(
        'title: "Older"\nslug: "older"\nexcerpt: "Older excerpt."\npublishedAt: "2026-03-01"',
      ),
      "/content/blog/newer.md": createMarkdown(
        'title: "Newer"\nslug: "newer"\nexcerpt: "Newer excerpt."\npublishedAt: "2026-04-01"',
      ),
    })

    // Assert
    expect(posts.map((post) => post.slug)).toEqual(["newer", "older"])
  })

  test("blog_content_draft_posts_excludes_from_public_results", () => {
    // Arrange / Act
    const posts = parseBlogPostModules({
      "/content/blog/published.md": createMarkdown(
        'title: "Published"\nslug: "published"\nexcerpt: "Published excerpt."\npublishedAt: "2026-04-01"',
      ),
      "/content/blog/draft.md": createMarkdown(
        'title: "Draft"\nslug: "draft"\nexcerpt: "Draft excerpt."\npublishedAt: "2026-04-02"\ndraft: true',
      ),
    })

    // Assert
    expect(posts).toHaveLength(1)
    expect(posts[0]?.slug).toBe("published")
  })

  test("blog_content_yaml_arrays_and_boolean_flags_parses_expected_values", () => {
    // Arrange / Act
    const post = parseBlogPostModule(
      "/content/blog/post.md",
      createMarkdown(
        'title: "Post"\nslug: "post"\nexcerpt: "Post excerpt."\npublishedAt: "2026-04-01"\ndraft: false\ntags:\n  - creators\n  - strategy',
      ),
    )

    // Assert
    expect(post.draft).toBe(false)
    expect(post.tags).toEqual(["creators", "strategy"])
  })

  test("blog_content_markdown_body_sanitizes_html_and_computes_reading_time", () => {
    // Arrange / Act
    const post = parseBlogPostModule(
      "/content/blog/post.md",
      createMarkdown(
        'title: "Post"\nslug: "post"\nexcerpt: "Post excerpt."\npublishedAt: "2026-04-01"',
        "# Heading\n\nParagraph with **bold** text.",
      ),
    )

    // Assert
    expect(post.html).toMatch(/<h1[^>]*>Heading<\/h1>/)
    expect(post.html).toMatch(/<strong>bold<\/strong>/)
    expect(post.readingTime).toBe(1)
  })

  test("blog_content_unsafe_markdown_links_and_images_drops_unsafe_markup", () => {
    // Arrange / Act
    const post = parseBlogPostModule(
      "/content/blog/post.md",
      createMarkdown(
        'title: "Post"\nslug: "post"\nexcerpt: "Post excerpt."\npublishedAt: "2026-04-01"',
        [
          '[Unsafe link](javascript:alert("xss"))',
          "",
          '![Unsafe image](javascript:alert("xss"))',
          "",
          "[Safe link](/blog)",
        ].join("\n"),
      ),
    )

    // Assert
    expect(post.html).not.toMatch(/javascript:/i)
    expect(post.html).toMatch(/>Unsafe link<\/p>/)
    expect(post.html).not.toMatch(/<img[^>]+Unsafe image/i)
    expect(post.html).toMatch(/<a href="\/blog">Safe link<\/a>/)
  })

  test("blog_content_duplicate_leading_h1_removes_title_heading_only", () => {
    // Arrange / Act
    const post = parseBlogPostModule(
      "/content/blog/post.md",
      createMarkdown(
        'title: "Post"\nslug: "post"\nexcerpt: "Post excerpt."\npublishedAt: "2026-04-01"',
        "# Post\n\n## Section\n\nParagraph.",
      ),
    )

    // Assert
    expect(post.html).not.toMatch(/<h1[^>]*>Post<\/h1>/)
    expect(post.html).toMatch(/<h2[^>]*>Section<\/h2>/)
    expect(post.html).toMatch(/<p>Paragraph\.<\/p>/)
  })

  test("blog_content_seo_defaults_resolves_canonical_and_open_graph_urls", () => {
    // Arrange / Act
    const post = parseBlogPostModule(
      "/content/blog/post.md",
      createMarkdown(
        'title: "Post"\nslug: "post"\nexcerpt: "Post excerpt."\npublishedAt: "2026-04-01"\ncoverImage: "/assets/blog/post.png"',
      ),
      { siteUrl: "https://kiizama.com/" },
    )

    // Assert
    expect(post.seoTitle).toBe("Post")
    expect(post.metaDescription).toBe("Post excerpt.")
    expect(post.canonicalUrl).toBe("https://kiizama.com/blog/post")
    expect(post.ogTitle).toBe("Post")
    expect(post.ogDescription).toBe("Post excerpt.")
    expect(post.ogImage).toBe("https://kiizama.com/assets/blog/post.png")
    expect(post.robots).toBe("index,follow")
  })

  test("blog_content_published_post_builds_article_json_ld", () => {
    // Arrange
    const post = parseBlogPostModule(
      "/content/blog/post.md",
      createMarkdown(
        'title: "Post"\nslug: "post"\nexcerpt: "Post excerpt."\npublishedAt: "2026-04-01"\nauthor: "Kiizama Team"',
      ),
      { siteUrl: "https://kiizama.com" },
    )

    // Act
    const seo = buildBlogPostSeo(post)

    // Assert
    expect(seo.jsonLd["@type"]).toBe("Article")
    expect(seo.jsonLd.headline).toBe("Post")
    expect(seo.jsonLd.mainEntityOfPage).toBe("https://kiizama.com/blog/post")
  })

  test("blog_content_missing_required_field_throws_validation_error", () => {
    // Arrange / Act / Assert
    expect(() =>
      parseBlogPostModules({
        "/content/blog/invalid.md": createMarkdown(
          'slug: "invalid"\nexcerpt: "Missing title."\npublishedAt: "2026-04-01"',
        ),
      }),
    ).toThrow(/"title" must be a non-empty string/)
  })

  test("blog_content_invalid_published_at_throws_validation_error", () => {
    // Arrange / Act / Assert
    expect(() =>
      parseBlogPostModules({
        "/content/blog/invalid-date.md": createMarkdown(
          'title: "Invalid date"\nslug: "invalid-date"\nexcerpt: "Invalid date excerpt."\npublishedAt: "04-01-2026"',
        ),
      }),
    ).toThrow(/"publishedAt" must be an ISO date or datetime string/)
  })

  test("blog_content_duplicate_slug_throws_validation_error", () => {
    // Arrange / Act / Assert
    expect(() =>
      parseBlogPostModules({
        "/content/blog/first.md": createMarkdown(
          'title: "First"\nslug: "duplicate"\nexcerpt: "First excerpt."\npublishedAt: "2026-04-01"',
        ),
        "/content/blog/second.md": createMarkdown(
          'title: "Second"\nslug: "duplicate"\nexcerpt: "Second excerpt."\npublishedAt: "2026-04-02"',
        ),
      }),
    ).toThrow(/Duplicate blog slug "duplicate"/)
  })

  test("blog_content_inline_html_throws_validation_error", () => {
    // Arrange / Act / Assert
    expect(() =>
      parseBlogPostModule(
        "/content/blog/html.md",
        createMarkdown(
          'title: "HTML"\nslug: "html"\nexcerpt: "HTML excerpt."\npublishedAt: "2026-04-01"',
          "<div>raw html</div>",
        ),
      ),
    ).toThrow(/inline HTML is not allowed/)
  })

  test("blog_content_invalid_canonical_url_throws_validation_error", () => {
    // Arrange / Act / Assert
    expect(() =>
      parseBlogPostModule(
        "/content/blog/post.md",
        createMarkdown(
          'title: "Post"\nslug: "post"\nexcerpt: "Post excerpt."\npublishedAt: "2026-04-01"\ncanonicalUrl: "blog/post"',
        ),
        { siteUrl: "https://kiizama.com" },
      ),
    ).toThrow(/"canonicalUrl" must be an absolute URL or a root-relative path/)
  })
})
