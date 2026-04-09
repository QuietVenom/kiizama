import type { TokensList } from "marked"
import { marked } from "marked"

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

type ParsedBlogPostFile = BlogPost & {
  sourcePath: string
}

type ParseBlogPostOptions = {
  siteUrl?: string
}

type ParsedFrontmatterModule = {
  content: string
  data: Record<string, unknown>
}

export const DEFAULT_SITE_URL = "https://kiizama.com"

const ISO_DATE_PATTERN = /^\d{4}-\d{2}-\d{2}$/
const ISO_DATETIME_PATTERN =
  /^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d{1,3})?(?:Z|[+-]\d{2}:\d{2})$/
const ABSOLUTE_HTTP_URL_PATTERN = /^https?:\/\//i
const WORDS_PER_MINUTE = 200
const SAFE_LINK_PROTOCOLS = new Set(["http:", "https:", "mailto:", "tel:"])
const SAFE_IMAGE_PROTOCOLS = new Set(["http:", "https:"])

marked.setOptions({
  async: false,
  breaks: false,
  gfm: true,
})

const escapeHtml = (value: string) =>
  value
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#39;")

const normalizeMarkdownUrl = (
  value: string,
  allowedProtocols: Set<string>,
): string | null => {
  const normalizedValue = value.trim()

  if (normalizedValue.length === 0) {
    return null
  }

  if (
    normalizedValue.startsWith("/") ||
    normalizedValue.startsWith("./") ||
    normalizedValue.startsWith("../") ||
    normalizedValue.startsWith("#")
  ) {
    return normalizedValue
  }

  try {
    const parsedUrl = new URL(normalizedValue)
    return allowedProtocols.has(parsedUrl.protocol) ? normalizedValue : null
  } catch {
    return null
  }
}

const renderer = new marked.Renderer()

renderer.link = ({ href, title, tokens }) => {
  const renderedText = renderer.parser.parseInline(tokens)
  const safeHref = normalizeMarkdownUrl(href, SAFE_LINK_PROTOCOLS)

  if (safeHref === null) {
    return renderedText
  }

  const titleAttribute =
    typeof title === "string" && title.length > 0
      ? ` title="${escapeHtml(title)}"`
      : ""

  return `<a href="${escapeHtml(safeHref)}"${titleAttribute}>${renderedText}</a>`
}

renderer.image = ({ href, title, text }) => {
  const safeHref = normalizeMarkdownUrl(href, SAFE_IMAGE_PROTOCOLS)

  if (safeHref === null) {
    return ""
  }

  const titleAttribute =
    typeof title === "string" && title.length > 0
      ? ` title="${escapeHtml(title)}"`
      : ""

  return `<img src="${escapeHtml(safeHref)}" alt="${escapeHtml(text)}"${titleAttribute}>`
}

const isRecord = (value: unknown): value is Record<string, unknown> =>
  typeof value === "object" && value !== null && !Array.isArray(value)

export const normalizeSiteUrl = (siteUrl: string) => siteUrl.replace(/\/+$/, "")

const isValidIsoDate = (value: string) => {
  if (!ISO_DATE_PATTERN.test(value) && !ISO_DATETIME_PATTERN.test(value)) {
    return false
  }

  const timestamp = Date.parse(value)
  return !Number.isNaN(timestamp)
}

const assertStringField = (
  value: unknown,
  fieldName: keyof BlogPostFrontmatter,
  sourcePath: string,
) => {
  if (typeof value !== "string" || value.trim().length === 0) {
    throw new Error(
      `Invalid blog frontmatter in "${sourcePath}": "${fieldName}" must be a non-empty string.`,
    )
  }

  return value.trim()
}

const assertOptionalStringField = (
  value: unknown,
  fieldName: keyof BlogPostFrontmatter,
  sourcePath: string,
) => {
  if (typeof value === "undefined") {
    return undefined
  }

  if (typeof value !== "string" || value.trim().length === 0) {
    throw new Error(
      `Invalid blog frontmatter in "${sourcePath}": "${fieldName}" must be a non-empty string when provided.`,
    )
  }

  return value.trim()
}

const assertOptionalStringArrayField = (
  value: unknown,
  fieldName: keyof BlogPostFrontmatter,
  sourcePath: string,
) => {
  if (typeof value === "undefined") {
    return undefined
  }

  if (
    !Array.isArray(value) ||
    value.some((item) => typeof item !== "string" || item.trim().length === 0)
  ) {
    throw new Error(
      `Invalid blog frontmatter in "${sourcePath}": "${fieldName}" must be an array of non-empty strings when provided.`,
    )
  }

  return value.map((item) => item.trim())
}

const assertOptionalBooleanField = (
  value: unknown,
  fieldName: keyof BlogPostFrontmatter,
  sourcePath: string,
) => {
  if (typeof value === "undefined") {
    return undefined
  }

  if (typeof value !== "boolean") {
    throw new Error(
      `Invalid blog frontmatter in "${sourcePath}": "${fieldName}" must be a boolean when provided.`,
    )
  }

  return value
}

const resolveAbsoluteUrl = (
  value: string | undefined,
  fieldName: keyof BlogPostFrontmatter,
  sourcePath: string,
  siteUrl: string,
) => {
  if (typeof value === "undefined") {
    return undefined
  }

  if (ABSOLUTE_HTTP_URL_PATTERN.test(value)) {
    return value
  }

  if (value.startsWith("/")) {
    return `${siteUrl}${value}`
  }

  throw new Error(
    `Invalid blog frontmatter in "${sourcePath}": "${fieldName}" must be an absolute URL or a root-relative path.`,
  )
}

const containsRawHtml = (markdown: string) => {
  const tokens = marked.lexer(markdown)

  const visit = (tokenList: unknown[]): boolean => {
    for (const token of tokenList) {
      if (!isRecord(token)) {
        continue
      }

      if (token.type === "html") {
        return true
      }

      const nestedTokens = token.tokens
      if (Array.isArray(nestedTokens) && visit(nestedTokens)) {
        return true
      }

      const items = token.items
      if (Array.isArray(items)) {
        for (const item of items) {
          if (isRecord(item)) {
            const itemTokens = item.tokens
            if (Array.isArray(itemTokens) && visit(itemTokens)) {
              return true
            }
          }
        }
      }
    }

    return false
  }

  return visit(tokens as unknown[])
}

const estimateReadingTime = (markdown: string) => {
  const wordCount = markdown
    .replace(/```[\s\S]*?```/g, " ")
    .replace(/`[^`]+`/g, " ")
    .replace(/[#>*_[\]()-]/g, " ")
    .trim()
    .split(/\s+/)
    .filter(Boolean).length

  return Math.max(1, Math.ceil(wordCount / WORDS_PER_MINUTE))
}

const stripLeadingTitleHeading = (
  tokens: TokensList,
  title: string,
): TokensList => {
  const normalizedTitle = title.trim()
  const nextTokens = [...tokens]
  let firstContentIndex = 0

  while (
    firstContentIndex < nextTokens.length &&
    nextTokens[firstContentIndex]?.type === "space"
  ) {
    firstContentIndex += 1
  }

  const firstContentToken = nextTokens[firstContentIndex]
  if (
    firstContentToken?.type === "heading" &&
    firstContentToken.depth === 1 &&
    firstContentToken.text.trim() === normalizedTitle
  ) {
    nextTokens.splice(firstContentIndex, 1)

    if (nextTokens[firstContentIndex]?.type === "space") {
      nextTokens.splice(firstContentIndex, 1)
    }
  }

  return Object.assign(nextTokens, {
    links: tokens.links,
  }) as TokensList
}

const FRONTMATTER_DELIMITER = "---"

const parseScalarValue = (rawValue: string): unknown => {
  const value = rawValue.trim()

  if (
    (value.startsWith('"') && value.endsWith('"')) ||
    (value.startsWith("'") && value.endsWith("'"))
  ) {
    return value.slice(1, -1)
  }

  if (value === "true") {
    return true
  }

  if (value === "false") {
    return false
  }

  return value
}

const parseFrontmatterModule = (
  rawMarkdown: string,
  sourcePath: string,
): ParsedFrontmatterModule => {
  const normalizedMarkdown = rawMarkdown.replace(/\r\n/g, "\n")

  if (!normalizedMarkdown.startsWith(`${FRONTMATTER_DELIMITER}\n`)) {
    return {
      content: normalizedMarkdown,
      data: {},
    }
  }

  const lines = normalizedMarkdown.split("\n")
  const closingDelimiterLine = lines.findIndex(
    (line, index) => index > 0 && line.trim() === FRONTMATTER_DELIMITER,
  )

  if (closingDelimiterLine === -1) {
    throw new Error(
      `Invalid blog frontmatter in "${sourcePath}": missing closing delimiter.`,
    )
  }

  const data: Record<string, unknown> = {}
  let pendingArrayKey: string | null = null

  for (const line of lines.slice(1, closingDelimiterLine)) {
    const trimmedLine = line.trim()

    if (trimmedLine.length === 0) {
      continue
    }

    if (trimmedLine.startsWith("#")) {
      continue
    }

    const arrayItemMatch = line.match(/^\s*-\s+(.*)$/)
    if (arrayItemMatch) {
      if (!pendingArrayKey) {
        throw new Error(
          `Invalid blog frontmatter in "${sourcePath}": array item found without a parent field.`,
        )
      }

      const currentValue = data[pendingArrayKey]
      if (!Array.isArray(currentValue)) {
        throw new Error(
          `Invalid blog frontmatter in "${sourcePath}": "${pendingArrayKey}" must be declared before its list items.`,
        )
      }

      currentValue.push(parseScalarValue(arrayItemMatch[1] ?? ""))
      continue
    }

    const fieldMatch = line.match(/^([A-Za-z][\w]*)\s*:\s*(.*)$/)
    if (!fieldMatch) {
      throw new Error(
        `Invalid blog frontmatter in "${sourcePath}": unsupported line "${line}".`,
      )
    }

    const [, key, rawValue] = fieldMatch

    if (typeof key === "undefined") {
      throw new Error(
        `Invalid blog frontmatter in "${sourcePath}": malformed field declaration.`,
      )
    }

    if (rawValue.trim().length === 0) {
      data[key] = []
      pendingArrayKey = key
      continue
    }

    data[key] = parseScalarValue(rawValue)
    pendingArrayKey = null
  }

  return {
    content: lines
      .slice(closingDelimiterLine + 1)
      .join("\n")
      .replace(/^\n+/, ""),
    data,
  }
}

const parseFrontmatter = (
  frontmatter: unknown,
  sourcePath: string,
): BlogPostFrontmatter => {
  if (!isRecord(frontmatter)) {
    throw new Error(
      `Invalid blog frontmatter in "${sourcePath}": expected an object.`,
    )
  }

  const publishedAt = assertStringField(
    frontmatter.publishedAt,
    "publishedAt",
    sourcePath,
  )

  if (!isValidIsoDate(publishedAt)) {
    throw new Error(
      `Invalid blog frontmatter in "${sourcePath}": "publishedAt" must be an ISO date or datetime string.`,
    )
  }

  return {
    title: assertStringField(frontmatter.title, "title", sourcePath),
    slug: assertStringField(frontmatter.slug, "slug", sourcePath),
    excerpt: assertStringField(frontmatter.excerpt, "excerpt", sourcePath),
    publishedAt,
    author: assertOptionalStringField(frontmatter.author, "author", sourcePath),
    coverImage: assertOptionalStringField(
      frontmatter.coverImage,
      "coverImage",
      sourcePath,
    ),
    tags: assertOptionalStringArrayField(frontmatter.tags, "tags", sourcePath),
    draft: assertOptionalBooleanField(frontmatter.draft, "draft", sourcePath),
    seoTitle: assertOptionalStringField(
      frontmatter.seoTitle,
      "seoTitle",
      sourcePath,
    ),
    metaDescription: assertOptionalStringField(
      frontmatter.metaDescription,
      "metaDescription",
      sourcePath,
    ),
    canonicalUrl: assertOptionalStringField(
      frontmatter.canonicalUrl,
      "canonicalUrl",
      sourcePath,
    ),
    ogTitle: assertOptionalStringField(
      frontmatter.ogTitle,
      "ogTitle",
      sourcePath,
    ),
    ogDescription: assertOptionalStringField(
      frontmatter.ogDescription,
      "ogDescription",
      sourcePath,
    ),
    ogImage: assertOptionalStringField(
      frontmatter.ogImage,
      "ogImage",
      sourcePath,
    ),
    robots: assertOptionalStringField(frontmatter.robots, "robots", sourcePath),
  }
}

const resolveSeoFields = (
  frontmatter: BlogPostFrontmatter,
  sourcePath: string,
  siteUrl: string,
) => {
  const normalizedSiteUrl = normalizeSiteUrl(siteUrl)
  const canonicalUrl =
    resolveAbsoluteUrl(
      frontmatter.canonicalUrl,
      "canonicalUrl",
      sourcePath,
      normalizedSiteUrl,
    ) ?? `${normalizedSiteUrl}/blog/${frontmatter.slug}`

  const normalizedCoverImage = resolveAbsoluteUrl(
    frontmatter.coverImage,
    "coverImage",
    sourcePath,
    normalizedSiteUrl,
  )
  const ogImage =
    resolveAbsoluteUrl(
      frontmatter.ogImage,
      "ogImage",
      sourcePath,
      normalizedSiteUrl,
    ) ?? normalizedCoverImage

  return {
    seoTitle: frontmatter.seoTitle ?? frontmatter.title,
    metaDescription: frontmatter.metaDescription ?? frontmatter.excerpt,
    canonicalUrl,
    ogTitle: frontmatter.ogTitle ?? frontmatter.seoTitle ?? frontmatter.title,
    ogDescription:
      frontmatter.ogDescription ??
      frontmatter.metaDescription ??
      frontmatter.excerpt,
    ogImage,
    robots: frontmatter.robots ?? "index,follow",
    coverImage: normalizedCoverImage,
  }
}

export const parseBlogPostModule = (
  sourcePath: string,
  rawMarkdown: string,
  options: ParseBlogPostOptions = {},
): ParsedBlogPostFile => {
  const { content, data } = parseFrontmatterModule(rawMarkdown, sourcePath)
  const frontmatter = parseFrontmatter(data, sourcePath)
  const siteUrl = normalizeSiteUrl(options.siteUrl ?? DEFAULT_SITE_URL)

  if (containsRawHtml(content)) {
    throw new Error(
      `Invalid blog markdown in "${sourcePath}": inline HTML is not allowed.`,
    )
  }

  const tokens = marked.lexer(content)
  const html = marked.parser(
    stripLeadingTitleHeading(tokens, frontmatter.title),
    { renderer },
  ) as string

  return {
    ...frontmatter,
    ...resolveSeoFields(frontmatter, sourcePath, siteUrl),
    html,
    readingTime: estimateReadingTime(content),
    sourcePath,
  }
}

export const parseBlogPostModules = (
  modules: Record<string, string>,
  options: ParseBlogPostOptions = {},
): BlogPost[] => {
  const posts = Object.entries(modules).map(([sourcePath, rawMarkdown]) =>
    parseBlogPostModule(sourcePath, rawMarkdown, options),
  )
  const uniqueSlugs = new Set<string>()

  for (const post of posts) {
    if (uniqueSlugs.has(post.slug)) {
      throw new Error(
        `Duplicate blog slug "${post.slug}" found in blog content.`,
      )
    }
    uniqueSlugs.add(post.slug)
  }

  return posts
    .filter((post) => post.draft !== true)
    .sort(
      (left, right) =>
        Date.parse(right.publishedAt) - Date.parse(left.publishedAt),
    )
    .map(({ sourcePath: _sourcePath, ...post }) => post)
}
