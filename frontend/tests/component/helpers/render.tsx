import { QueryClient, QueryClientProvider } from "@tanstack/react-query"
import { type RenderOptions, render } from "@testing-library/react"
import type { PropsWithChildren, ReactElement } from "react"

import { CustomProvider } from "../../../src/components/ui/provider"

export const createTestQueryClient = () =>
  new QueryClient({
    defaultOptions: {
      queries: {
        retry: false,
        gcTime: 0,
      },
      mutations: {
        retry: false,
      },
    },
  })

type RenderWithProvidersOptions = RenderOptions & {
  queryClient?: QueryClient
}

export const renderWithProviders = (
  ui: ReactElement,
  options: RenderWithProvidersOptions = {},
) => {
  const { queryClient = createTestQueryClient(), ...renderOptions } = options

  const Wrapper = ({ children }: PropsWithChildren) => (
    <CustomProvider>
      <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
    </CustomProvider>
  )

  return {
    queryClient,
    ...render(ui, { wrapper: Wrapper, ...renderOptions }),
  }
}
