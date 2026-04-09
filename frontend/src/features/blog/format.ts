const blogDateFormatter = new Intl.DateTimeFormat("en-US", {
  day: "numeric",
  month: "long",
  year: "numeric",
})

export const formatBlogPublishedAt = (publishedAt: string) => {
  const parsedDate = new Date(publishedAt)

  if (Number.isNaN(parsedDate.getTime())) {
    return publishedAt
  }

  return blogDateFormatter.format(parsedDate)
}
