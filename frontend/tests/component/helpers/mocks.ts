import { vi } from "vitest"

export const mockToast = () => ({
  showSuccessToast: vi.fn(),
  showErrorToast: vi.fn(),
})

export const mockNavigate = () => vi.fn()

export const mockAuth = () => ({
  error: null as string | null,
  resetError: vi.fn(),
  loginMutation: {
    mutateAsync: vi.fn(),
    isPending: false,
  },
  signUpMutation: {
    mutate: vi.fn(),
    isPending: false,
  },
})

export const mockClientService = <T extends object>(service: T) => service
