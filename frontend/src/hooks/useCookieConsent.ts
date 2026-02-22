import { useEffect, useRef, useState } from "react"

export type CookiePreferenceKey = "functional" | "analytics" | "marketing"

export type CookiePreferences = {
  strictlyNecessary: true
  functional: boolean
  analytics: boolean
  marketing: boolean
}

export type CookieConsentOption = {
  key: "strictlyNecessary" | CookiePreferenceKey
  label: string
  editable: boolean
}

const COOKIE_CONSENT_NAME = "notion_cookie_consent"

export const DEFAULT_COOKIE_PREFERENCES: CookiePreferences = {
  strictlyNecessary: true,
  functional: true,
  analytics: true,
  marketing: true,
}

export const COOKIE_CONSENT_OPTIONS: CookieConsentOption[] = [
  { key: "strictlyNecessary", label: "Strictly Necessary", editable: false },
  { key: "functional", label: "Functional", editable: true },
  { key: "analytics", label: "Analytics", editable: true },
  { key: "marketing", label: "Marketing", editable: true },
]

const parseCookiePreferences = (rawValue: string): CookiePreferences | null => {
  try {
    const decodedValue = decodeURIComponent(rawValue)
    const parsed = JSON.parse(decodedValue) as Partial<CookiePreferences>
    return {
      strictlyNecessary: true,
      functional: Boolean(parsed.functional),
      analytics: Boolean(parsed.analytics),
      marketing: Boolean(parsed.marketing),
    }
  } catch {
    return null
  }
}

export const readCookiePreferences = (): CookiePreferences | null => {
  if (typeof document === "undefined") {
    return null
  }

  const cookieValue = document.cookie
    .split("; ")
    .find((entry) => entry.startsWith(`${COOKIE_CONSENT_NAME}=`))

  if (!cookieValue) {
    return null
  }

  const rawValue = cookieValue.slice(COOKIE_CONSENT_NAME.length + 1)
  return parseCookiePreferences(rawValue)
}

export const writeCookiePreferences = (preferences: CookiePreferences) => {
  if (typeof document === "undefined") {
    return
  }

  const maxAge = 60 * 60 * 24 * 365
  const value = encodeURIComponent(JSON.stringify(preferences))
  // biome-ignore lint/suspicious/noDocumentCookie: consent preferences are intentionally stored in a first-party cookie for broad browser compatibility.
  document.cookie = `${COOKIE_CONSENT_NAME}=${value}; path=/; max-age=${maxAge}; SameSite=Lax`
}

export const ensureCookieConsentSaved = (): CookiePreferences => {
  const existingPreferences = readCookiePreferences()
  if (existingPreferences) {
    return existingPreferences
  }
  writeCookiePreferences(DEFAULT_COOKIE_PREFERENCES)
  return DEFAULT_COOKIE_PREFERENCES
}

type UseCookieConsentOptions = {
  panelAnimationMs?: number
}

type UseCookieConsentReturn = {
  cookiePreferences: CookiePreferences
  isCookiePanelMounted: boolean
  isCookiePanelVisible: boolean
  cookiePanelAnimationMs: number
  openCookiePanel: () => void
  closeCookiePanel: () => void
  updateCookiePreference: (
    key: CookiePreferenceKey,
    checked: boolean | "indeterminate",
  ) => void
  acceptAllCookies: () => void
  savePreferencesAndClose: () => void
}

export const useCookieConsent = (
  options: UseCookieConsentOptions = {},
): UseCookieConsentReturn => {
  const { panelAnimationMs = 280 } = options
  const [isCookiePanelMounted, setCookiePanelMounted] = useState(false)
  const [isCookiePanelVisible, setCookiePanelVisible] = useState(false)
  const [cookiePreferences, setCookiePreferences] = useState<CookiePreferences>(
    DEFAULT_COOKIE_PREFERENCES,
  )
  const closePanelTimerRef = useRef<number | null>(null)

  useEffect(() => {
    const savedPreferences = readCookiePreferences()
    if (savedPreferences) {
      setCookiePreferences(savedPreferences)
    }
  }, [])

  useEffect(() => {
    return () => {
      if (closePanelTimerRef.current !== null) {
        window.clearTimeout(closePanelTimerRef.current)
      }
    }
  }, [])

  const clearClosePanelTimer = () => {
    if (closePanelTimerRef.current === null) {
      return
    }
    window.clearTimeout(closePanelTimerRef.current)
    closePanelTimerRef.current = null
  }

  const openCookiePanel = () => {
    clearClosePanelTimer()
    const savedPreferences = readCookiePreferences()
    setCookiePreferences(savedPreferences ?? DEFAULT_COOKIE_PREFERENCES)
    setCookiePanelMounted(true)
    window.requestAnimationFrame(() => {
      setCookiePanelVisible(true)
    })
  }

  const closeCookiePanel = () => {
    clearClosePanelTimer()
    setCookiePanelVisible(false)
    closePanelTimerRef.current = window.setTimeout(() => {
      setCookiePanelMounted(false)
      closePanelTimerRef.current = null
    }, panelAnimationMs)
  }

  const updateCookiePreference = (
    key: CookiePreferenceKey,
    checked: boolean | "indeterminate",
  ) => {
    setCookiePreferences((current) => ({
      ...current,
      [key]: checked === true,
    }))
  }

  const acceptAllCookies = () => {
    setCookiePreferences(DEFAULT_COOKIE_PREFERENCES)
  }

  const savePreferencesAndClose = () => {
    writeCookiePreferences(cookiePreferences)
    closeCookiePanel()
  }

  return {
    cookiePreferences,
    isCookiePanelMounted,
    isCookiePanelVisible,
    cookiePanelAnimationMs: panelAnimationMs,
    openCookiePanel,
    closeCookiePanel,
    updateCookiePreference,
    acceptAllCookies,
    savePreferencesAndClose,
  }
}
