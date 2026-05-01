import { mkdir, readFile, writeFile } from "node:fs/promises"
import path from "node:path"
import dotenv from "dotenv"
import { getAllBlogPosts } from "../src/features/blog/content.ts"
import {
  buildBlogIndexSeo,
  buildBlogPostSeo,
} from "../src/features/blog/seo.ts"
import type { BlogPost } from "../src/features/blog/types.ts"
import {
  DEFAULT_SITE_URL,
  normalizeSiteUrl,
} from "../src/features/blog/types.ts"

const projectRoot = path.resolve(import.meta.dirname, "..")
const repoRoot = path.resolve(projectRoot, "..")
const distDir = path.join(projectRoot, "dist")

dotenv.config({ path: path.join(repoRoot, ".env") })

const siteUrl = normalizeSiteUrl(process.env.VITE_SITE_URL || DEFAULT_SITE_URL)

const escapeHtml = (value: string) =>
  value
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")

const stripManagedHead = (html: string) =>
  html.replace(/<title>[\s\S]*?<\/title>/, "")

const injectHead = (html: string, headMarkup: string) =>
  html.replace("</head>", `${headMarkup}\n  </head>`)

const injectRootMarkup = (html: string, rootMarkup: string) =>
  html.replace('<div id="root"></div>', `<div id="root">${rootMarkup}</div>`)

const renderHeadMarkup = (
  seo:
    | ReturnType<typeof buildBlogIndexSeo>
    | ReturnType<typeof buildBlogPostSeo>,
) => {
  const tags = [
    `<title>${escapeHtml(seo.title)}</title>`,
    ...seo.meta.map((entry) => {
      if ("name" in entry) {
        return `<meta name="${escapeHtml(entry.name)}" content="${escapeHtml(entry.content)}" />`
      }

      return `<meta property="${escapeHtml(entry.property)}" content="${escapeHtml(entry.content)}" />`
    }),
    ...seo.links.map(
      (link) =>
        `<link rel="${escapeHtml(link.rel)}" href="${escapeHtml(link.href)}" />`,
    ),
    `<script type="application/ld+json">${JSON.stringify(seo.jsonLd)}</script>`,
  ]

  return tags.join("\n  ")
}

const renderBlogIndexRoot = (posts: BlogPost[]) => {
  const articles = posts
    .map(
      (post) => `
      <article>
        <h2><a href="/blog/${post.slug}">${escapeHtml(post.title)}</a></h2>
        <p>${escapeHtml(post.metaDescription)}</p>
        <p><small>${escapeHtml(post.publishedAt)} · ${post.readingTime} min read</small></p>
      </article>`,
    )
    .join("\n")

  return `
    <main>
      <header>
        <p>Kiizama Journal</p>
        <h1>The latest Kiizama insights</h1>
        <p>Product thinking, workflow notes, and reputation intelligence perspectives from Kiizama.</p>
      </header>
      <section>
        ${articles}
      </section>
    </main>`
}

const renderBlogPostRoot = (post: BlogPost) => {
  const tags = post.tags?.length
    ? `<p>${post.tags.map((tag) => escapeHtml(tag)).join(" · ")}</p>`
    : ""
  const author = post.author ? `<p>By ${escapeHtml(post.author)}</p>` : ""

  return `
    <main>
      <article>
        <p><a href="/blog">Back to blog</a></p>
        <h1>${escapeHtml(post.title)}</h1>
        <p>${escapeHtml(post.metaDescription)}</p>
        <p><small>${escapeHtml(post.publishedAt)} · ${post.readingTime} min read</small></p>
        ${author}
        ${tags}
        ${post.html}
      </article>
    </main>`
}

const buildSitemap = (posts: BlogPost[]) => {
  const urls = [
    `${siteUrl}/`,
    `${siteUrl}/blog`,
    ...posts.map((post) => post.canonicalUrl),
  ]

  return `<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
${urls
  .map(
    (url) => `  <url>
    <loc>${escapeHtml(url)}</loc>
  </url>`,
  )
  .join("\n")}
</urlset>
`
}

const buildRobots = () => `User-agent: *
Allow: /

Sitemap: ${siteUrl}/sitemap.xml
`

const writePrerenderedPage = async (
  outputPath: string,
  baseHtml: string,
  headMarkup: string,
  rootMarkup: string,
) => {
  await mkdir(path.dirname(outputPath), { recursive: true })
  const htmlWithHead = injectHead(stripManagedHead(baseHtml), headMarkup)
  const finalHtml = injectRootMarkup(htmlWithHead, rootMarkup)
  await writeFile(outputPath, finalHtml, "utf8")
}

const main = async () => {
  const baseHtml = await readFile(path.join(distDir, "index.html"), "utf8")
  const posts = getAllBlogPosts()
  const blogIndexSeo = buildBlogIndexSeo(posts, siteUrl)

  await writeFile(path.join(distDir, "robots.txt"), buildRobots(), "utf8")
  await writeFile(
    path.join(distDir, "sitemap.xml"),
    buildSitemap(posts),
    "utf8",
  )

  await writePrerenderedPage(
    path.join(distDir, "blog", "index.html"),
    baseHtml,
    renderHeadMarkup(blogIndexSeo),
    renderBlogIndexRoot(posts),
  )

  for (const post of posts) {
    await writePrerenderedPage(
      path.join(distDir, "blog", post.slug, "index.html"),
      baseHtml,
      renderHeadMarkup(buildBlogPostSeo(post)),
      renderBlogPostRoot(post),
    )
  }
}

await main()
