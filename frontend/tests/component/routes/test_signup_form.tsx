import { screen, waitFor } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import type { ReactNode } from "react"
import { beforeEach, describe, expect, test, vi } from "vitest"

import { renderWithProviders } from "../helpers/render"

const signUpMutation = {
  mutate: vi.fn(),
  isPending: false,
}
const toast = {
  showErrorToast: vi.fn(),
}

vi.mock("@tanstack/react-router", () => ({
  createFileRoute: () => (config: unknown) => config,
  Link: ({
    children,
    to,
    className,
  }: {
    children: ReactNode
    to: string
    className?: string
  }) => (
    <a className={className} href={to}>
      {children}
    </a>
  ),
  redirect: vi.fn(),
}))

vi.mock("@/hooks/useAuth", () => ({
  default: () => ({ signUpMutation }),
}))

vi.mock("@/hooks/useCustomToast", () => ({
  default: () => toast,
}))

vi.mock("@/hooks/useFeatureFlags", () => ({
  isPublicFeatureFlagEnabled: vi.fn().mockResolvedValue(false),
}))

vi.mock("@/components/Common/ThemeLogo", () => ({
  default: () => <span>Kiizama</span>,
}))

const legalDocuments = {
  simplified_notice: "Read and accept required legal documents.",
  documents: [
    {
      type: "privacy_notice",
      url: "https://example.com/privacy",
    },
    {
      type: "terms_conditions",
      url: "https://example.com/terms",
    },
  ],
}

vi.mock("@/client", async (importOriginal) => {
  const actual = await importOriginal<typeof import("@/client")>()
  return {
    ...actual,
    PublicLegalDocumentsService: {
      listPublicLegalDocuments: vi.fn().mockResolvedValue(legalDocuments),
    },
  }
})

const { SignUpPage } = await import(
  "../../../src/routes/-components/SignUpPage"
)

const fillValidSignupForm = async () => {
  const user = userEvent.setup()
  await user.type(screen.getByPlaceholderText("Nombre completo"), "Test User")
  await user.type(
    screen.getByPlaceholderText("Correo electrónico"),
    "user@example.com",
  )
  await user.type(screen.getByPlaceholderText("Contraseña"), "Aa1!valid")
  await user.type(
    screen.getByPlaceholderText("Confirmar contraseña"),
    "Aa1!valid",
  )
  return user
}

describe("signup form", () => {
  beforeEach(() => {
    signUpMutation.mutate.mockClear()
    signUpMutation.isPending = false
    toast.showErrorToast.mockClear()
  })

  test("signup_form_initial_state_renders_required_fields_and_login_link", () => {
    // Arrange / Act
    renderWithProviders(<SignUpPage />)

    // Assert
    expect(screen.getByPlaceholderText("Nombre completo")).toBeVisible()
    expect(screen.getByPlaceholderText("Correo electrónico")).toBeVisible()
    expect(screen.getByPlaceholderText("Contraseña")).toBeVisible()
    expect(screen.getByPlaceholderText("Confirmar contraseña")).toBeVisible()
    expect(screen.getByText("Requisitos de contraseña")).toBeVisible()
    expect(
      screen.getByRole("link", { name: "Iniciar sesión" }),
    ).toHaveAttribute("href", "/login")
  })

  test("signup_form_empty_fields_shows_required_validation_errors", async () => {
    // Arrange
    const user = userEvent.setup()
    renderWithProviders(<SignUpPage />)

    // Act
    await user.click(screen.getByRole("button", { name: "Crear cuenta" }))

    // Assert
    expect(
      await screen.findByText("El nombre completo es obligatorio"),
    ).toBeVisible()
    expect(
      await screen.findByText("El correo electrónico es obligatorio"),
    ).toBeVisible()
    expect(
      await screen.findByText("La contraseña es obligatoria"),
    ).toBeVisible()
    expect(
      await screen.findByText("La confirmación de contraseña es obligatoria"),
    ).toBeVisible()
  })

  test("signup_form_invalid_email_weak_password_and_mismatch_show_errors", async () => {
    // Arrange
    const user = userEvent.setup()
    renderWithProviders(<SignUpPage />)

    // Act
    await user.type(screen.getByPlaceholderText("Nombre completo"), "Test User")
    await user.type(
      screen.getByPlaceholderText("Correo electrónico"),
      "bad-email",
    )
    await user.type(screen.getByPlaceholderText("Contraseña"), "weak")
    await user.type(
      screen.getByPlaceholderText("Confirmar contraseña"),
      "different",
    )
    await user.click(screen.getByRole("button", { name: "Crear cuenta" }))

    // Assert
    expect(await screen.findByText("Correo electrónico inválido")).toBeVisible()
    expect(
      await screen.findByText(
        "La contraseña debe tener entre 8 y 25 caracteres",
      ),
    ).toBeVisible()
    expect(
      await screen.findByText("Las contraseñas no coinciden"),
    ).toBeVisible()
  })

  test("signup_form_valid_submit_opens_legal_modal_with_disabled_confirm", async () => {
    // Arrange
    renderWithProviders(<SignUpPage />)
    const user = await fillValidSignupForm()

    // Act
    await user.click(screen.getByRole("button", { name: "Crear cuenta" }))

    // Assert
    expect(await screen.findByTestId("signup-legal-modal")).toBeVisible()
    expect(screen.getByTestId("confirm-legal-acceptance")).toBeDisabled()
    expect(screen.getByTestId("privacy-link")).toHaveAttribute(
      "href",
      "https://example.com/privacy",
    )
    expect(screen.getByTestId("terms-link")).toHaveAttribute(
      "href",
      "https://example.com/terms",
    )
  })

  test("signup_form_accepting_legal_documents_calls_signup_with_acceptances", async () => {
    // Arrange
    renderWithProviders(<SignUpPage />)
    const user = await fillValidSignupForm()
    await user.click(screen.getByRole("button", { name: "Crear cuenta" }))
    await screen.findByTestId("signup-legal-modal")

    // Act
    await user.click(screen.getByTestId("accept-privacy-checkbox"))
    await user.click(screen.getByTestId("accept-terms-checkbox"))
    await user.click(screen.getByTestId("confirm-legal-acceptance"))

    // Assert
    await waitFor(() => {
      expect(signUpMutation.mutate).toHaveBeenCalledWith(
        {
          email: "user@example.com",
          full_name: "Test User",
          password: "Aa1!valid",
          legal_acceptances: {
            privacy_notice: true,
            terms_conditions: true,
          },
        },
        expect.any(Object),
      )
    })
  })
})
