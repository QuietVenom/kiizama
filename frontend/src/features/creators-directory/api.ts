import { IgProfilesService } from "@/client"
import type {
  CreatorDirectoryFullProfileResponse,
  CreatorDirectorySearchRequest,
  CreatorDirectorySearchResponse,
} from "./types"

export const searchCreatorsDirectory = (
  request: CreatorDirectorySearchRequest,
): Promise<CreatorDirectorySearchResponse> =>
  IgProfilesService.searchIgProfiles({
    query: request.query,
    aiCategories: request.ai_categories,
    aiRoles: request.ai_roles,
    followerCountMin: request.follower_count_min,
    followerCountMax: request.follower_count_max,
    sortBy: request.sort_by,
    sortOrder: request.sort_order,
    page: request.page,
    pageSize: request.page_size,
  })

export const getCreatorDirectoryFullProfile = (
  profileId: string,
): Promise<CreatorDirectoryFullProfileResponse> =>
  IgProfilesService.readIgProfileFullProfile({
    profileId,
  })
