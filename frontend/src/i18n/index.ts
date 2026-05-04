import i18n from "i18next"
import LanguageDetector from "i18next-browser-languagedetector"
import { initReactI18next } from "react-i18next"
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
      order: ["localStorage", "navigator"],
      caches: ["localStorage"],
      lookupLocalStorage: LANGUAGE_STORAGE_KEY,
      convertDetectedLanguage: (language: string) =>
        normalizeLanguage(language),
    },
  })

i18n.on("languageChanged", syncDocumentLanguage)
syncDocumentLanguage(i18n.resolvedLanguage ?? i18n.language)

export default i18n

export * from "./constants"
export * from "./format"
