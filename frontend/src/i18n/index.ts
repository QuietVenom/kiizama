import i18n from "i18next"
import LanguageDetector from "i18next-browser-languagedetector"
import { initReactI18next } from "react-i18next"
import { writeCookie } from "@/lib/browser-cookies"
import {
  COOKIE_MAX_AGE_ONE_YEAR_MINUTES,
  getSharedCookieOptions,
} from "@/lib/cookie-settings"
import {
  DEFAULT_LANGUAGE,
  I18N_NAMESPACES,
  LANGUAGE_STORAGE_KEY,
  SUPPORTED_LANGUAGES,
} from "./constants"
import { normalizeLanguage } from "./format"
import { resources } from "./resources"

const syncDocumentLanguage = (language?: string) => {
  if (typeof document === "undefined") {
    return
  }

  document.documentElement.lang = normalizeLanguage(language)
}

const getNormalizedSupportedLanguage = (language?: string | null) => {
  if (!language) {
    return null
  }

  const normalizedLanguage = normalizeLanguage(language)
  return SUPPORTED_LANGUAGES.includes(normalizedLanguage)
    ? normalizedLanguage
    : null
}

const writeLanguageCookie = (language: string) => {
  const normalizedLanguage = getNormalizedSupportedLanguage(language)
  if (!normalizedLanguage) {
    return
  }

  writeCookie(
    LANGUAGE_STORAGE_KEY,
    normalizedLanguage,
    getSharedCookieOptions(),
  )
}

void i18n
  .use(LanguageDetector)
  .use(initReactI18next)
  .init({
    resources,
    fallbackLng: DEFAULT_LANGUAGE,
    supportedLngs: SUPPORTED_LANGUAGES,
    ns: I18N_NAMESPACES,
    defaultNS: "common",
    fallbackNS: "common",
    load: "currentOnly",
    interpolation: {
      escapeValue: false,
    },
    detection: {
      order: ["cookie", "navigator"],
      caches: ["cookie"],
      lookupCookie: LANGUAGE_STORAGE_KEY,
      cookieMinutes: COOKIE_MAX_AGE_ONE_YEAR_MINUTES,
      cookieDomain: getSharedCookieOptions().domain,
      cookieOptions: {
        path: "/",
        sameSite: "lax",
        secure: getSharedCookieOptions().secure,
      },
      convertDetectedLanguage: (language: string) =>
        normalizeLanguage(language),
    },
  })

i18n.on("languageChanged", (language) => {
  syncDocumentLanguage(language)
  writeLanguageCookie(language)
})
syncDocumentLanguage(i18n.resolvedLanguage ?? i18n.language)

export default i18n

export * from "./constants"
export * from "./format"
