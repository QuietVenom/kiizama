import { formatDate, type SupportedLanguage } from "@/i18n"

const ISO_DATE_PATTERN = /^\d{4}-\d{2}-\d{2}$/

const parseBlogPublishedAt = (publishedAt: string) => {
  if (ISO_DATE_PATTERN.test(publishedAt)) {
    const [year, month, day] = publishedAt.split("-").map(Number)

    return new Date(Date.UTC(year, month - 1, day))
  }

  return new Date(publishedAt)
}

export const formatBlogPublishedAt = (
  publishedAt: string,
  language?: SupportedLanguage | string | null,
) => {
  const parsedDate = parseBlogPublishedAt(publishedAt)

  if (Number.isNaN(parsedDate.getTime())) {
    return publishedAt
  }

  return formatDate(parsedDate, language, {
    day: "numeric",
    month: "long",
    year: "numeric",
    ...(ISO_DATE_PATTERN.test(publishedAt) ? { timeZone: "UTC" } : {}),
  })
}
