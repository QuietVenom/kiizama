import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import { useNavigate } from "@tanstack/react-router"
import { useState } from "react"

import {
  type Body_login_login_access_token as AccessToken,
  type ApiError,
  LoginService,
  type UserPublic,
  type UserRegister,
  UsersService,
} from "@/client"
import { clearUserEventsCursor } from "@/features/user-events/cursor"
import { handleError } from "@/utils"

const CURRENT_USER_STALE_TIME_MS = 5 * 60 * 1000

const isLoggedIn = () => {
  return localStorage.getItem("access_token") !== null
}

const currentUserQueryOptions = {
  queryKey: ["currentUser"] as const,
  queryFn: UsersService.readUserMe,
  staleTime: CURRENT_USER_STALE_TIME_MS,
}

const useAuth = () => {
  const [error, setError] = useState<string | null>(null)
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const { data: user } = useQuery<UserPublic, Error>({
    ...currentUserQueryOptions,
    enabled: isLoggedIn(),
  })

  const signUpMutation = useMutation({
    mutationFn: (data: UserRegister) =>
      UsersService.registerUser({ requestBody: data }),

    onSuccess: () => {
      navigate({ to: "/login" })
    },
    onError: (err: ApiError) => {
      handleError(err)
    },
    onSettled: () => {
      queryClient.invalidateQueries({ queryKey: ["users"] })
    },
  })

  const login = async (data: AccessToken) => {
    const response = await LoginService.loginAccessToken({
      formData: data,
    })
    localStorage.setItem("access_token", response.access_token)
  }

  const loginMutation = useMutation({
    mutationFn: login,
    onSuccess: () => {
      navigate({ to: "/overview" })
    },
    onError: (err: ApiError) => {
      handleError(err)
    },
  })

  const logout = () => {
    const currentUserId =
      user?.id ??
      queryClient.getQueryData<UserPublic>(currentUserQueryOptions.queryKey)?.id

    if (currentUserId) {
      clearUserEventsCursor(currentUserId)
    }
    localStorage.removeItem("access_token")
    navigate({ to: "/login" })
  }

  return {
    signUpMutation,
    loginMutation,
    logout,
    user,
    error,
    resetError: () => setError(null),
  }
}

export { isLoggedIn }
export { currentUserQueryOptions }
export default useAuth
