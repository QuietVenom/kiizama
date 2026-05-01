import { screen, waitFor } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import type { ReactNode } from "react"
import { beforeEach, describe, expect, test, vi } from "vitest"

import {
  DEFAULT_COOKIE_PREFERENCES,
  readCookiePreferences,
  writeCookiePreferences,
} from "../../../src/hooks/useCookieConsent"
import { renderWithProviders } from "../helpers/render"

vi.mock("@tanstack/react-router", () => ({
  Link: ({
    children,
    className,
    to,
  }: {
    children: ReactNode
    className?: string
    to: string
  }) => (
    <a className={className} href={to}>
      {children}
    </a>
  ),
}))

const CookieConsentPrompt = (
  await import("../../../src/components/Common/CookieConsentPrompt")
).default

const clearCookieConsent = () => {
  // biome-ignore lint/suspicious/noDocumentCookie: this test must reset the browser cookie boundary before each case.
  document.cookie =
    "notion_cookie_consent=; path=/; expires=Thu, 01 Jan 1970 00:00:00 GMT"
}

describe("cookie consent prompt", () => {
  beforeEach(() => {
    clearCookieConsent()
  })

  test("cookie_consent_prompt_without_saved_cookie_renders_choices_and_notice_link", async () => {
    // Arrange / Act
    renderWithProviders(<CookieConsentPrompt />)

    // Assert
    expect(await screen.findByRole("dialog")).toBeVisible()
    expect(screen.getByText("This website uses cookies")).toBeVisible()
    expect(screen.getByRole("link", { name: "Cookie Notice" })).toHaveAttribute(
      "href",
      "/cookie-notice",
    )
    expect(
      screen.getByRole("button", { name: "Allow all cookies" }),
    ).toBeVisible()
    expect(
      screen.getByRole("button", { name: "Allow necessary cookies" }),
    ).toBeVisible()
  })

  test("cookie_consent_prompt_allow_all_persists_default_preferences", async () => {
    // Arrange
    const user = userEvent.setup()
    renderWithProviders(<CookieConsentPrompt />)

    // Act
    await user.click(
      await screen.findByRole("button", { name: "Allow all cookies" }),
    )

    // Assert
    await waitFor(() => {
      expect(screen.queryByRole("dialog")).not.toBeInTheDocument()
    })
    expect(readCookiePreferences()).toEqual(DEFAULT_COOKIE_PREFERENCES)
  })

  test("cookie_consent_prompt_necessary_only_persists_rejected_optional_preferences", async () => {
    // Arrange
    const user = userEvent.setup()
    renderWithProviders(<CookieConsentPrompt />)

    // Act
    await user.click(
      await screen.findByRole("button", { name: "Allow necessary cookies" }),
    )

    // Assert
    await waitFor(() => {
      expect(screen.queryByRole("dialog")).not.toBeInTheDocument()
    })
    expect(readCookiePreferences()).toEqual({
      analytics: false,
      functional: false,
      marketing: false,
      strictlyNecessary: true,
    })
  })

  test("cookie_consent_prompt_with_existing_cookie_does_not_render", () => {
    // Arrange
    writeCookiePreferences(DEFAULT_COOKIE_PREFERENCES)

    // Act
    renderWithProviders(<CookieConsentPrompt />)

    // Assert
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument()
  })
})
