import { describe, expect, test } from "vitest"

import { formatBillingDateOnly } from "../../../../src/features/billing/date"

const billingDateFormatter = new Intl.DateTimeFormat("es-MX", {
  day: "2-digit",
  month: "long",
  year: "numeric",
})

describe("billing date formatting", () => {
  test("billing_date_empty_values_return_null", () => {
    // Arrange / Act / Assert
    expect(formatBillingDateOnly(null)).toBeNull()
    expect(formatBillingDateOnly(undefined)).toBeNull()
  })

  test("billing_date_date_only_value_formats_without_timezone_day_shift", () => {
    // Arrange
    const expected = billingDateFormatter.format(new Date(2026, 0, 31))

    // Act
    const result = formatBillingDateOnly("2026-01-31")

    // Assert
    expect(result).toBe(expected)
  })

  test("billing_date_iso_datetime_formats_valid_date", () => {
    // Arrange
    const isoDate = "2026-02-03T12:00:00.000Z"
    const expected = billingDateFormatter.format(new Date(isoDate))

    // Act
    const result = formatBillingDateOnly(isoDate)

    // Assert
    expect(result).toBe(expected)
  })

  test("billing_date_invalid_value_returns_original_string", () => {
    // Arrange / Act
    const result = formatBillingDateOnly("not-a-date")

    // Assert
    expect(result).toBe("not-a-date")
  })
})
