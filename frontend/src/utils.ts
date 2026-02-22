import type { ApiError } from "./client"
import useCustomToast from "./hooks/useCustomToast"

export const emailPattern = {
  value: /^[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}$/i,
  message: "Invalid email address",
}

export const namePattern = {
  value: /^[A-Za-z\s\u00C0-\u017F]{1,30}$/,
  message: "Invalid name",
}

export const passwordRules = (isRequired = true) => {
  const rules: any = {
    minLength: {
      value: 8,
      message: "Password must be at least 8 characters",
    },
  }

  if (isRequired) {
    rules.required = "Password is required"
  }

  return rules
}

export const confirmPasswordRules = (
  getValues: () => any,
  isRequired = true,
) => {
  const rules: any = {
    validate: (value: string) => {
      const password = getValues().password || getValues().new_password
      return value === password ? true : "The passwords do not match"
    },
  }

  if (isRequired) {
    rules.required = "Password confirmation is required"
  }

  return rules
}

export const handleError = (err: ApiError) => {
  const { showErrorToast } = useCustomToast()
  const errDetail = (err.body as any)?.detail
  let errorMessage = errDetail || "Something went wrong."
  if (Array.isArray(errDetail) && errDetail.length > 0) {
    errorMessage = errDetail[0].msg
  }
  showErrorToast(errorMessage)
}

export const getAppOrigin = (): string => {
  if (typeof window === "undefined") return ""

  const { protocol, hostname, port, origin } = window.location

  if (hostname.startsWith("app.")) {
    return origin
  }

  if (hostname.endsWith(".onrender.com")) {
    return origin
  }

  let targetHost = hostname
  if (hostname.startsWith("www.")) {
    targetHost = `app.${hostname.slice(4)}`
  } else if (hostname === "localhost" || hostname === "127.0.0.1") {
    targetHost = "app.localhost"
  } else {
    targetHost = `app.${hostname}`
  }

  const includePort = Boolean(port && port !== "80" && port !== "443")
  const portSegment = includePort ? `:${port}` : ""
  return `${protocol}//${targetHost}${portSegment}`
}

export const getAppUrl = (path: string): string => {
  const normalizedPath = path.startsWith("/") ? path : `/${path}`
  const origin = getAppOrigin()
  return origin ? `${origin}${normalizedPath}` : normalizedPath
}

export const getWwwOrigin = (): string => {
  if (typeof window === "undefined") return ""

  const { protocol, hostname, port, origin } = window.location

  if (hostname.startsWith("www.")) {
    return origin
  }

  if (hostname.endsWith(".onrender.com")) {
    return origin
  }

  let targetHost = hostname
  if (hostname.startsWith("app.")) {
    targetHost = `www.${hostname.slice(4)}`
  } else if (hostname === "localhost" || hostname === "127.0.0.1") {
    targetHost = "www.localhost"
  } else {
    targetHost = `www.${hostname}`
  }

  const includePort = Boolean(port && port !== "80" && port !== "443")
  const portSegment = includePort ? `:${port}` : ""
  return `${protocol}//${targetHost}${portSegment}`
}

export const getWwwUrl = (path: string): string => {
  const normalizedPath = path.startsWith("/") ? path : `/${path}`
  const origin = getWwwOrigin()
  return origin ? `${origin}${normalizedPath}` : normalizedPath
}
