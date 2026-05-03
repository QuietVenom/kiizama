import { QueryClient, QueryClientProvider } from "@tanstack/react-query"
import { type RenderOptions, render } from "@testing-library/react"
import type { PropsWithChildren, ReactElement } from "react"

import { CustomProvider } from "../../../src/components/ui/provider"
import type { SupportedLanguage } from "../../../src/i18n"
import i18n, { DEFAULT_LANGUAGE, LANGUAGE_STORAGE_KEY } from "../../../src/i18n"

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
  language?: SupportedLanguage
  queryClient?: QueryClient
}

export const renderWithProviders = (
  ui: ReactElement,
  options: RenderWithProvidersOptions = {},
) => {
  const {
    language = DEFAULT_LANGUAGE,
    queryClient = createTestQueryClient(),
    ...renderOptions
  } = options

  localStorage.setItem(LANGUAGE_STORAGE_KEY, language)
  i18n.services.languageDetector?.cacheUserLanguage(language)
  i18n.language = language
  i18n.languages = [language]
  i18n.resolvedLanguage = language
  document.documentElement.lang = language
  i18n.emit("languageChanged", language)

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
