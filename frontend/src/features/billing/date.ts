import { formatDate } from "@/i18n"

const DATE_ONLY_PATTERN = /^(\d{4})-(\d{2})-(\d{2})$/

export const formatBillingDateOnly = (
  value: string | null | undefined,
  language?: string | null,
) => {
  if (!value) {
    return null
  }

  const match = DATE_ONLY_PATTERN.exec(value)
  if (match) {
    const [, year, month, day] = match
    return formatDate(
      new Date(Date.UTC(Number(year), Number(month) - 1, Number(day))),
      language,
      {
        day: "2-digit",
        month: "long",
        year: "numeric",
        timeZone: "UTC",
      },
    )
  }

  const parsed = new Date(value)
  if (Number.isNaN(parsed.getTime())) {
    return value
  }

  return formatDate(parsed, language, {
    day: "2-digit",
    month: "long",
    year: "numeric",
  })
}
