export const LANGUAGE_STORAGE_KEY = "kiizama.language"

export const SUPPORTED_LANGUAGES = ["es", "en", "pt-BR"] as const

export type SupportedLanguage = (typeof SUPPORTED_LANGUAGES)[number]

export const DEFAULT_LANGUAGE: SupportedLanguage = "es"

export const I18N_NAMESPACES = [
  "common",
  "landing",
  "auth",
  "settings",
  "dashboard",
  "billing",
  "creatorsSearch",
  "brandIntelligence",
] as const

export type I18nNamespace = (typeof I18N_NAMESPACES)[number]
