import type { TFunction } from "i18next"
import type {
  CreatorDirectoryAppliedFilters,
  CreatorDirectoryProfile,
} from "./types"

const FRESHNESS_THRESHOLD_DAYS = 4

const millisecondsInDay = 1000 * 60 * 60 * 24

export const normalizeDirectoryQuery = (value: string) => {
  const trimmed = value.trim()
  return trimmed.length >= 3 ? trimmed : undefined
}

export const buildCreatorDirectoryRequest = ({
  page,
  query,
  filters,
}: {
  page: number
  query: string
  filters: CreatorDirectoryAppliedFilters
}) => ({
  ...filters,
  page,
  query: normalizeDirectoryQuery(query),
})

export const getDirectoryProfileStatus = ({
  profile,
  t,
  now = Date.now(),
}: {
  profile: CreatorDirectoryProfile
  t: TFunction<"creatorsSearch">
  now?: number
}) => {
  return isDirectoryProfileCurrent(profile, now)
    ? t("directoryPreview.results.status.current")
    : t("directoryPreview.results.status.update")
}

export const isDirectoryProfileCurrent = (
  profile: CreatorDirectoryProfile,
  now = Date.now(),
) => {
  const updatedAt = Date.parse(profile.updated_date)
  if (Number.isNaN(updatedAt)) {
    return false
  }

  const ageInDays = (now - updatedAt) / millisecondsInDay
  return ageInDays < FRESHNESS_THRESHOLD_DAYS
}

export const getDirectoryProfilePrimaryLabel = (
  profile: CreatorDirectoryProfile,
  t: TFunction<"creatorsSearch">,
) => {
  const categories = (profile.ai_categories ?? []).filter(Boolean)
  if (categories.length > 0) {
    return categories.slice(0, 2).join(", ")
  }

  return t("directoryPreview.results.fallbackCategory")
}

export const getDirectoryProfileRoleLabel = (
  profile: CreatorDirectoryProfile,
  t: TFunction<"creatorsSearch">,
) => {
  const roles = (profile.ai_roles ?? []).filter(Boolean)
  if (roles.length > 0) {
    return roles.slice(0, 2).join(", ")
  }

  return t("directoryPreview.results.fallbackRole")
}

export const formatCompactCount = (value: number, language: string) =>
  new Intl.NumberFormat(language, {
    notation: "compact",
    maximumFractionDigits: value >= 100_000 ? 0 : 1,
  }).format(value)
