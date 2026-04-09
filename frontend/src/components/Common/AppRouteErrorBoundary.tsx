import type { ErrorComponentProps } from "@tanstack/react-router"
import { useRouter } from "@tanstack/react-router"
import { useEffect } from "react"
import Forbidden from "@/components/Common/Forbidden"
import ServerError from "@/components/Common/ServerError"
import ServiceUnavailable from "@/components/Common/ServiceUnavailable"
import { type AppErrorSource, normalizeAppError } from "@/features/errors/http"
import { redirectToLoginWithReturnTo } from "@/features/errors/navigation"

type AppRouteErrorBoundaryProps = ErrorComponentProps & {
  source?: AppErrorSource
}

const AppRouteErrorBoundary = ({
  error,
  reset,
  source = "router",
}: AppRouteErrorBoundaryProps) => {
  const router = useRouter()
  const normalizedError = normalizeAppError(error, source)

  useEffect(() => {
    if (normalizedError.status === 401) {
      redirectToLoginWithReturnTo(router.latestLocation.href)
    }
  }, [normalizedError.status, router.latestLocation.href])

  if (normalizedError.status === 401) {
    return null
  }

  if (normalizedError.status === 403) {
    return <Forbidden />
  }

  const handleRetry = () => {
    reset()
    router.invalidate()
  }

  if (normalizedError.status === 503) {
    return (
      <ServiceUnavailable
        message={normalizedError.message}
        onRetry={handleRetry}
      />
    )
  }

  return <ServerError message={normalizedError.message} onRetry={handleRetry} />
}

export default AppRouteErrorBoundary
