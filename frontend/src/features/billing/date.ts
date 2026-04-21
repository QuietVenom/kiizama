const billingDateFormatter = new Intl.DateTimeFormat("es-MX", {
  day: "2-digit",
  month: "long",
  year: "numeric",
})

const DATE_ONLY_PATTERN = /^(\d{4})-(\d{2})-(\d{2})$/

export const formatBillingDateOnly = (value: string | null | undefined) => {
  if (!value) {
    return null
  }

  const match = DATE_ONLY_PATTERN.exec(value)
  if (match) {
    const [, year, month, day] = match
    return billingDateFormatter.format(
      new Date(Number(year), Number(month) - 1, Number(day)),
    )
  }

  const parsed = new Date(value)
  if (Number.isNaN(parsed.getTime())) {
    return value
  }

  return billingDateFormatter.format(parsed)
}
