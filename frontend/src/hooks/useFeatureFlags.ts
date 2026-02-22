import { useMutation } from "@tanstack/react-query"

const API_BASE_URL = import.meta.env.VITE_API_URL
const PUBLIC_FEATURE_FLAGS_PATH = "/api/v1/public/feature-flags"

export type PublicFeatureFlag = {
  key: string
  description: string | null
  is_enabled: boolean
  is_public: boolean
}

const getPublicFeatureFlagUrl = (flagKey: string) =>
  `${API_BASE_URL}${PUBLIC_FEATURE_FLAGS_PATH}/${encodeURIComponent(flagKey)}`

export const fetchPublicFeatureFlag = async (
  flagKey: string,
): Promise<PublicFeatureFlag | null> => {
  const response = await fetch(getPublicFeatureFlagUrl(flagKey))
  if (response.status === 404) {
    return null
  }

  const body = (await response.json()) as
    | PublicFeatureFlag
    | { detail?: string | Array<{ msg?: string }> }

  if (!response.ok) {
    const detail = (body as { detail?: string | Array<{ msg?: string }> })
      .detail
    if (Array.isArray(detail) && detail.length > 0) {
      throw new Error(detail[0]?.msg || "Unable to load feature flag")
    }
    throw new Error((detail as string) || "Unable to load feature flag")
  }

  return body as PublicFeatureFlag
}

export const isPublicFeatureFlagEnabled = async (
  flagKey: string,
): Promise<boolean> => {
  const flag = await fetchPublicFeatureFlag(flagKey)
  return Boolean(flag?.is_public && flag.is_enabled)
}

export const usePublicFeatureFlagMutation = () =>
  useMutation({
    mutationFn: (flagKey: string) => fetchPublicFeatureFlag(flagKey),
  })
