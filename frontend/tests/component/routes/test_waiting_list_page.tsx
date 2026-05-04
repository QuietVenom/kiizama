import { screen, waitFor } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import type { ReactNode } from "react"
import { beforeEach, describe, expect, test, vi } from "vitest"

import { renderWithProviders } from "../helpers/render"

const toast = {
  showErrorToast: vi.fn(),
  showSuccessToast: vi.fn(),
}

vi.mock("@tanstack/react-router", () => ({
  Link: ({ children, to }: { children: ReactNode; to: string }) => (
    <a href={to}>{children}</a>
  ),
}))

vi.mock("@/components/Common/ThemeLogo", () => ({
  default: () => <span>Kiizama</span>,
}))

vi.mock("@/hooks/useCustomToast", () => ({
  default: () => toast,
}))

const { WaitingListPage } = await import(
  "../../../src/routes/-components/WaitingListPage"
)

describe("waiting list page", () => {
  beforeEach(() => {
    toast.showErrorToast.mockClear()
    toast.showSuccessToast.mockClear()
    vi.unstubAllGlobals()
  })

  test("waiting_list_page_initial_state_renders_form_controls", () => {
    // Arrange / Act
    renderWithProviders(<WaitingListPage />)

    // Assert
    expect(screen.getByText("Únete a nuestra lista de espera")).toBeVisible()
    expect(screen.getByRole("combobox")).toBeVisible()
    expect(screen.getByPlaceholderText("Correo electrónico")).toBeVisible()
    expect(screen.getByRole("button", { name: "Enviar" })).toBeVisible()
    expect(
      screen.getByRole("button", { name: "Ir a la landing" }),
    ).toBeVisible()
    expect(
      screen.getByRole("link", { name: "Símbolo de Kiizama" }),
    ).toHaveAttribute("href", "/")
  })

  test("waiting_list_page_empty_submit_shows_validation_errors", async () => {
    // Arrange
    const user = userEvent.setup()
    renderWithProviders(<WaitingListPage />)

    // Act
    await user.click(screen.getByRole("button", { name: "Enviar" }))

    // Assert
    expect(await screen.findByText("Selecciona una opción")).toBeVisible()
    expect(
      await screen.findByText("El correo electrónico es obligatorio"),
    ).toBeVisible()
  })

  test("waiting_list_page_success_posts_payload_resets_form_and_shows_toast", async () => {
    // Arrange
    const user = userEvent.setup()
    const fetchMock = vi.fn().mockResolvedValue({
      json: vi.fn().mockResolvedValue({ message: "Joined successfully" }),
      ok: true,
    })
    vi.stubGlobal("fetch", fetchMock)
    renderWithProviders(<WaitingListPage />)

    // Act
    await user.selectOptions(screen.getByRole("combobox"), "marketing")
    await user.type(
      screen.getByPlaceholderText("Correo electrónico"),
      "user@example.com",
    )
    await user.click(screen.getByRole("button", { name: "Enviar" }))

    // Assert
    await waitFor(() => {
      expect(fetchMock).toHaveBeenCalled()
      expect(toast.showSuccessToast).toHaveBeenCalledWith("Joined successfully")
    })
    const [url, init] = fetchMock.mock.calls[0] as [string, RequestInit]
    expect(url).toContain("/api/v1/public/waiting-list/")
    expect(init.method).toBe("POST")
    expect(JSON.parse(init.body as string)).toEqual({
      email: "user@example.com",
      interest: "marketing",
    })
    expect(screen.getByPlaceholderText("Correo electrónico")).toHaveValue("")
    expect(screen.getByRole("combobox")).toHaveValue("")
  })

  test("waiting_list_page_error_detail_shows_error_toast", async () => {
    // Arrange
    const user = userEvent.setup()
    const fetchMock = vi.fn().mockResolvedValue({
      json: vi.fn().mockResolvedValue({
        detail: [{ msg: "Email already registered" }],
      }),
      ok: false,
    })
    vi.stubGlobal("fetch", fetchMock)
    renderWithProviders(<WaitingListPage />)

    // Act
    await user.selectOptions(screen.getByRole("combobox"), "creator")
    await user.type(
      screen.getByPlaceholderText("Correo electrónico"),
      "user@example.com",
    )
    await user.click(screen.getByRole("button", { name: "Enviar" }))

    // Assert
    await waitFor(() => {
      expect(toast.showErrorToast).toHaveBeenCalledWith(
        "Email already registered",
      )
    })
  })
})
