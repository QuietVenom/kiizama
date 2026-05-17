import { useEffect, useRef, useState } from "react"
import { deleteCookie, readCookie, writeCookie } from "@/lib/browser-cookies"
import {
  COOKIE_CONSENT_NAME,
  getSharedCookieOptions,
  LEGACY_COOKIE_CONSENT_NAME,
} from "@/lib/cookie-settings"

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
  const currentPreferences = parseCookiePreferences(
    readCookie(COOKIE_CONSENT_NAME) ?? "",
  )

  if (currentPreferences) {
    return currentPreferences
  }

  const legacyPreferences = parseCookiePreferences(
    readCookie(LEGACY_COOKIE_CONSENT_NAME) ?? "",
  )

  if (!legacyPreferences) {
    return null
  }

  writeCookiePreferences(legacyPreferences)
  deleteCookie(LEGACY_COOKIE_CONSENT_NAME)
  deleteCookie(LEGACY_COOKIE_CONSENT_NAME, {
    domain: getSharedCookieOptions().domain,
    path: "/",
    sameSite: "Lax",
  })
  return legacyPreferences
}

export const writeCookiePreferences = (preferences: CookiePreferences) => {
  writeCookie(
    COOKIE_CONSENT_NAME,
    JSON.stringify(preferences),
    getSharedCookieOptions(),
  )
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
