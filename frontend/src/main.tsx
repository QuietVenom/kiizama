import {
  MutationCache,
  QueryCache,
  QueryClient,
  QueryClientProvider,
} from "@tanstack/react-query"
import { createRouter, RouterProvider } from "@tanstack/react-router"
import { StrictMode } from "react"
import ReactDOM from "react-dom/client"
import { ApiError, OpenAPI } from "./client"
import NotFound from "./components/Common/NotFound"
import { CustomProvider } from "./components/ui/provider"
import { normalizeAppError } from "./features/errors/http"
import { redirectToLoginWithReturnTo } from "./features/errors/navigation"
import "./i18n"
import { AppInstallProvider } from "./components/Installation/AppInstallProvider"
import { configureInstallationMetadata } from "./components/Installation/metadata"
import { routeTree } from "./routeTree.gen"

configureInstallationMetadata()

OpenAPI.BASE = import.meta.env.VITE_API_URL
OpenAPI.TOKEN = async () => {
  return localStorage.getItem("access_token") || ""
}

const handleApiError = (error: Error) => {
  if (error instanceof ApiError) {
    const normalizedError = normalizeAppError(error, "query")
    if (normalizedError.status === 401) {
      redirectToLoginWithReturnTo()
    }
  }
}
const queryClient = new QueryClient({
  queryCache: new QueryCache({
    onError: handleApiError,
  }),
  mutationCache: new MutationCache({
    onError: handleApiError,
  }),
})

const router = createRouter({
  routeTree,
  context: {
    queryClient,
  },
  defaultNotFoundComponent: NotFound,
  notFoundMode: "root",
})
declare module "@tanstack/react-router" {
  interface Register {
    router: typeof router
  }
}

ReactDOM.createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <CustomProvider>
      <QueryClientProvider client={queryClient}>
        <AppInstallProvider>
          <RouterProvider router={router} />
        </AppInstallProvider>
      </QueryClientProvider>
    </CustomProvider>
  </StrictMode>,
)
