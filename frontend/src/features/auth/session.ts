import { UsersService } from "@/client"

const getTokenStorage = () => {
  if (typeof localStorage === "undefined") {
    return undefined
  }

  return localStorage
}

export const getStoredAccessToken = () =>
  getTokenStorage()?.getItem("access_token") ?? null

export const hasStoredAccessToken = () => getStoredAccessToken() !== null

export const setStoredAccessToken = (token: string) => {
  getTokenStorage()?.setItem("access_token", token)
}

export const clearStoredAccessToken = () => {
  getTokenStorage()?.removeItem("access_token")
}

export const ensureValidStoredSession = async () => {
  if (!hasStoredAccessToken()) {
    return false
  }

  try {
    await UsersService.readUserMe()
    return true
  } catch {
    clearStoredAccessToken()
    return false
  }
}
