import type {
  Profile,
  ProfileSearchResponse,
  ProfileSnapshotFull,
} from "@/client"

export type CreatorDirectorySortBy = "username" | "follower_count"
export type CreatorDirectorySortOrder = "asc" | "desc"

export type CreatorDirectoryAppliedFilters = {
  query?: string
  ai_categories: string[]
  ai_roles: string[]
  follower_count_min: number
  follower_count_max?: number
  sort_by: CreatorDirectorySortBy
  sort_order: CreatorDirectorySortOrder
  page_size: number
}

export type CreatorDirectorySearchRequest = CreatorDirectoryAppliedFilters & {
  page: number
}

export type CreatorDirectorySearchResponse = ProfileSearchResponse

export type CreatorDirectoryProfile = Profile

export type CreatorDirectoryFullProfileResponse = ProfileSnapshotFull
