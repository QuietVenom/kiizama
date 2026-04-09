import assert from "node:assert/strict"
import test from "node:test"
import {
  parseBlogPostModule,
  parseBlogPostModules,
} from "../src/features/blog/parser.ts"
import { buildBlogPostSeo } from "../src/features/blog/seo.ts"

const createMarkdown = (
  frontmatter: string,
  body = "Hello world from Kiizama.",
) => `---\n${frontmatter}\n---\n\n${body}\n`

test("loads valid posts and orders them by publishedAt descending", () => {
  const posts = parseBlogPostModules({
    "/content/blog/older.md": createMarkdown(
      'title: "Older"\nslug: "older"\nexcerpt: "Older excerpt."\npublishedAt: "2026-03-01"',
    ),
    "/content/blog/newer.md": createMarkdown(
      'title: "Newer"\nslug: "newer"\nexcerpt: "Newer excerpt."\npublishedAt: "2026-04-01"',
    ),
  })

  assert.equal(posts.length, 2)
  assert.deepEqual(
    posts.map((post) => post.slug),
    ["newer", "older"],
  )
})

test("excludes draft posts from public results", () => {
  const posts = parseBlogPostModules({
    "/content/blog/published.md": createMarkdown(
      'title: "Published"\nslug: "published"\nexcerpt: "Published excerpt."\npublishedAt: "2026-04-01"',
    ),
    "/content/blog/draft.md": createMarkdown(
      'title: "Draft"\nslug: "draft"\nexcerpt: "Draft excerpt."\npublishedAt: "2026-04-02"\ndraft: true',
    ),
  })

  assert.equal(posts.length, 1)
  assert.equal(posts[0]?.slug, "published")
})

test("parses yaml-style arrays and boolean flags without node-only frontmatter helpers", () => {
  const post = parseBlogPostModule(
    "/content/blog/post.md",
    createMarkdown(
      'title: "Post"\nslug: "post"\nexcerpt: "Post excerpt."\npublishedAt: "2026-04-01"\ndraft: false\ntags:\n  - creators\n  - strategy',
    ),
  )

  assert.equal(post.draft, false)
  assert.deepEqual(post.tags, ["creators", "strategy"])
})

test("renders markdown to sanitized html and computes reading time", () => {
  const post = parseBlogPostModule(
    "/content/blog/post.md",
    createMarkdown(
      'title: "Post"\nslug: "post"\nexcerpt: "Post excerpt."\npublishedAt: "2026-04-01"',
      "# Heading\n\nParagraph with **bold** text.",
    ),
  )

  assert.match(post.html, /<h1[^>]*>Heading<\/h1>/)
  assert.match(post.html, /<strong>bold<\/strong>/)
  assert.equal(post.readingTime, 1)
})

test("drops unsafe markdown links and images", () => {
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

  assert.doesNotMatch(post.html, /javascript:/i)
  assert.match(post.html, />Unsafe link<\/p>/)
  assert.doesNotMatch(post.html, /<img[^>]+Unsafe image/i)
  assert.match(post.html, /<a href="\/blog">Safe link<\/a>/)
})

test("drops a leading h1 when it duplicates the frontmatter title", () => {
  const post = parseBlogPostModule(
    "/content/blog/post.md",
    createMarkdown(
      'title: "Post"\nslug: "post"\nexcerpt: "Post excerpt."\npublishedAt: "2026-04-01"',
      "# Post\n\n## Section\n\nParagraph.",
    ),
  )

  assert.doesNotMatch(post.html, /<h1[^>]*>Post<\/h1>/)
  assert.match(post.html, /<h2[^>]*>Section<\/h2>/)
  assert.match(post.html, /<p>Paragraph\.<\/p>/)
})

test("applies SEO defaults and resolves canonical URLs from the site URL", () => {
  const post = parseBlogPostModule(
    "/content/blog/post.md",
    createMarkdown(
      'title: "Post"\nslug: "post"\nexcerpt: "Post excerpt."\npublishedAt: "2026-04-01"\ncoverImage: "/assets/blog/post.png"',
    ),
    { siteUrl: "https://kiizama.com/" },
  )

  assert.equal(post.seoTitle, "Post")
  assert.equal(post.metaDescription, "Post excerpt.")
  assert.equal(post.canonicalUrl, "https://kiizama.com/blog/post")
  assert.equal(post.ogTitle, "Post")
  assert.equal(post.ogDescription, "Post excerpt.")
  assert.equal(post.ogImage, "https://kiizama.com/assets/blog/post.png")
  assert.equal(post.robots, "index,follow")
})

test("builds article JSON-LD for a published post", () => {
  const post = parseBlogPostModule(
    "/content/blog/post.md",
    createMarkdown(
      'title: "Post"\nslug: "post"\nexcerpt: "Post excerpt."\npublishedAt: "2026-04-01"\nauthor: "Kiizama Team"',
    ),
    { siteUrl: "https://kiizama.com" },
  )
  const seo = buildBlogPostSeo(post)

  assert.equal(seo.jsonLd["@type"], "Article")
  assert.equal(seo.jsonLd.headline, "Post")
  assert.equal(seo.jsonLd.mainEntityOfPage, "https://kiizama.com/blog/post")
})

test("throws when a required field is missing", () => {
  assert.throws(
    () =>
      parseBlogPostModules({
        "/content/blog/invalid.md": createMarkdown(
          'slug: "invalid"\nexcerpt: "Missing title."\npublishedAt: "2026-04-01"',
        ),
      }),
    /"title" must be a non-empty string/,
  )
})

test("throws when publishedAt is not a valid ISO string", () => {
  assert.throws(
    () =>
      parseBlogPostModules({
        "/content/blog/invalid-date.md": createMarkdown(
          'title: "Invalid date"\nslug: "invalid-date"\nexcerpt: "Invalid date excerpt."\npublishedAt: "04-01-2026"',
        ),
      }),
    /"publishedAt" must be an ISO date or datetime string/,
  )
})

test("throws when duplicate slugs are present", () => {
  assert.throws(
    () =>
      parseBlogPostModules({
        "/content/blog/first.md": createMarkdown(
          'title: "First"\nslug: "duplicate"\nexcerpt: "First excerpt."\npublishedAt: "2026-04-01"',
        ),
        "/content/blog/second.md": createMarkdown(
          'title: "Second"\nslug: "duplicate"\nexcerpt: "Second excerpt."\npublishedAt: "2026-04-02"',
        ),
      }),
    /Duplicate blog slug "duplicate"/,
  )
})

test("throws when markdown contains inline html", () => {
  assert.throws(
    () =>
      parseBlogPostModule(
        "/content/blog/html.md",
        createMarkdown(
          'title: "HTML"\nslug: "html"\nexcerpt: "HTML excerpt."\npublishedAt: "2026-04-01"',
          "<div>raw html</div>",
        ),
      ),
    /inline HTML is not allowed/,
  )
})

test("throws when canonicalUrl is not absolute or root-relative", () => {
  assert.throws(
    () =>
      parseBlogPostModule(
        "/content/blog/post.md",
        createMarkdown(
          'title: "Post"\nslug: "post"\nexcerpt: "Post excerpt."\npublishedAt: "2026-04-01"\ncanonicalUrl: "blog/post"',
        ),
        { siteUrl: "https://kiizama.com" },
      ),
    /"canonicalUrl" must be an absolute URL or a root-relative path/,
  )
})
