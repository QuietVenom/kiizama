import type { ProfileExistenceItem } from "@/client"
import { sanitizeInstagramUsernames } from "@/lib/instagram-usernames"

export const normalizeListValues = (value: string[]) =>
  Array.from(new Set(value.map((item) => item.trim()).filter(Boolean)))

export const normalizeUsernameList = (value: string[]) =>
  sanitizeInstagramUsernames(value)

export const isValidHttpUrl = (value: string) => {
  try {
    const parsedUrl = new URL(value)
    return ["http:", "https:"].includes(parsedUrl.protocol)
  } catch {
    return false
  }
}

export const buildProfileExistenceMap = (profiles: ProfileExistenceItem[]) =>
  new Map(profiles.map((profile) => [profile.username, profile] as const))

export const orderProfileExistence = (
  usernames: string[],
  profiles: ProfileExistenceItem[],
) => {
  const profileMap = buildProfileExistenceMap(profiles)

  return usernames.map(
    (username) =>
      profileMap.get(username) ?? {
        username,
        exists: false,
        expired: false,
      },
  )
}
