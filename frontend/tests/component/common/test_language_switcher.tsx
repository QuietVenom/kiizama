import { screen, waitFor } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import { describe, expect, test } from "vitest"

import LanguageSwitcher from "../../../src/components/Common/LanguageSwitcher"
import { LANGUAGE_STORAGE_KEY } from "../../../src/i18n"
import { renderWithProviders } from "../helpers/render"

describe("language switcher", () => {
  test("language_switcher_updates_active_language_and_persists_selection", async () => {
    const user = userEvent.setup()

    renderWithProviders(<LanguageSwitcher variant="settings" />, {
      language: "en",
    })

    expect(
      screen.getByRole("button", { name: "Select language" }),
    ).toHaveTextContent("English")

    await user.click(screen.getByRole("button", { name: "Select language" }))
    await user.click(await screen.findByText("Português (Brasil)"))

    await waitFor(() => {
      expect(localStorage.getItem(LANGUAGE_STORAGE_KEY)).toBe("pt-BR")
      expect(document.documentElement.lang).toBe("pt-BR")
      expect(
        screen.getByRole("button", { name: "Selecionar idioma" }),
      ).toHaveTextContent("Português (Brasil)")
    })
  })
})
