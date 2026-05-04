import {
  DEFAULT_LANGUAGE,
  SUPPORTED_LANGUAGES,
  type SupportedLanguage,
} from "./constants"

const DEFAULT_CURRENCY = "USD"

const supportedLanguages = new Set<string>(SUPPORTED_LANGUAGES)

export const normalizeLanguage = (
  language?: string | null,
): SupportedLanguage => {
  if (!language) {
    return DEFAULT_LANGUAGE
  }

  if (supportedLanguages.has(language)) {
    return language as SupportedLanguage
  }

  const lowercaseLanguage = language.toLowerCase()

  if (lowercaseLanguage.startsWith("pt")) {
    return "pt-BR"
  }

  if (lowercaseLanguage.startsWith("en")) {
    return "en"
  }

  return DEFAULT_LANGUAGE
}

export const getLocaleForLanguage = (language?: string | null): string =>
  normalizeLanguage(language)

type DateFormatOptions = Intl.DateTimeFormatOptions
type NumberFormatOptions = Intl.NumberFormatOptions

export const formatDate = (
  value: Date | string | number,
  language?: string | null,
  options?: DateFormatOptions,
) => {
  return new Intl.DateTimeFormat(
    getLocaleForLanguage(language),
    options,
  ).format(new Date(value))
}

export const formatNumber = (
  value: number,
  language?: string | null,
  options?: NumberFormatOptions,
) => {
  return new Intl.NumberFormat(getLocaleForLanguage(language), options).format(
    value,
  )
}

export const formatCurrency = (
  value: number,
  language?: string | null,
  currency = DEFAULT_CURRENCY,
  options?: Omit<NumberFormatOptions, "currency" | "style">,
) => {
  return new Intl.NumberFormat(getLocaleForLanguage(language), {
    style: "currency",
    currency,
    ...options,
  }).format(value)
}
