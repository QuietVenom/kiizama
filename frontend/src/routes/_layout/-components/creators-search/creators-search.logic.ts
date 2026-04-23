import type {
  ProfileSnapshotExpanded,
  ProfileSnapshotExpandedCollection,
} from "@/client"
import type { CreatorsSearchJobStatus } from "@/lib/creators-search-jobs"
import { MAX_INSTAGRAM_USERNAMES } from "@/lib/instagram-usernames"

export const MAX_USERNAMES = MAX_INSTAGRAM_USERNAMES
export const SEARCH_HISTORY_PREVIEW_LIMIT = 5
export const SEARCH_HISTORY_VIEW_ALL_LIMIT = 20

export type OverviewCardTone = "brand" | "success" | "warning" | "danger"

export const overviewToneStyles: Record<
  OverviewCardTone,
  { bg: string; color: string; labelColor: string }
> = {
  brand: {
    bg: "ui.brandSoft",
    color: "ui.brandText",
    labelColor: "ui.secondaryText",
  },
  success: {
    bg: "ui.successSoft",
    color: "ui.successText",
    labelColor: "ui.secondaryText",
  },
  warning: {
    bg: "ui.warningSoft",
    color: "ui.warningText",
    labelColor: "ui.secondaryText",
  },
  danger: {
    bg: "ui.dangerSoft",
    color: "ui.dangerText",
    labelColor: "ui.secondaryText",
  },
}

const jobTimestampFormatter = new Intl.DateTimeFormat("en-US", {
  day: "2-digit",
  hour: "2-digit",
  minute: "2-digit",
  month: "short",
})

export const creatorsSearchHistoryQueryKey = (limit?: number) =>
  limit === undefined
    ? (["creators-search-history"] as const)
    : (["creators-search-history", limit] as const)

export const getReadyUsernamesFromSearchResult = (
  requestedUsernames: string[],
  result: ProfileSnapshotExpandedCollection,
) => {
  const expiredUsernames = new Set(result.expired_usernames ?? [])
  const foundUsernames = new Set(
    (result.snapshots ?? [])
      .map((snapshot) => snapshot.profile?.username ?? "")
      .filter(Boolean),
  )

  return requestedUsernames.filter(
    (username) =>
      foundUsernames.has(username) && !expiredUsernames.has(username),
  )
}

export const formatJobTimestamp = (value: string) => {
  const parsedDate = new Date(value)
  if (Number.isNaN(parsedDate.getTime())) {
    return value
  }

  return jobTimestampFormatter.format(parsedDate)
}

export const getJobStatusStyles = (status: CreatorsSearchJobStatus) => {
  if (status === "done") {
    return {
      bg: "ui.successSoft",
      borderColor: "ui.success",
      textColor: "ui.successText",
    }
  }

  if (status === "failed") {
    return {
      bg: "ui.dangerSoft",
      borderColor: "ui.danger",
      textColor: "ui.dangerText",
    }
  }

  return {
    bg: "ui.infoSoft",
    borderColor: "ui.infoText",
    textColor: "ui.infoText",
  }
}

export const sortSnapshotsByUsernames = (
  snapshots: ProfileSnapshotExpanded[],
  usernames: string[],
) => {
  const usernameOrder = new Map(
    usernames.map((username, index) => [username, index] as const),
  )

  return [...snapshots].sort((left, right) => {
    const leftOrder =
      usernameOrder.get(left.profile?.username ?? "") ?? Number.MAX_SAFE_INTEGER
    const rightOrder =
      usernameOrder.get(right.profile?.username ?? "") ??
      Number.MAX_SAFE_INTEGER

    return leftOrder - rightOrder
  })
}

export const getValidationMessage = (
  invalidUsernames: string[],
  overflowAttempted: boolean,
) => {
  if (invalidUsernames.length > 0) {
    return `Invalid usernames: ${invalidUsernames
      .map((username) => `@${username}`)
      .join(
        ", ",
      )}. Use lowercase letters, numbers, periods or underscores, up to 30 characters.`
  }

  if (overflowAttempted) {
    return "You can search up to 50 usernames per request."
  }

  return undefined
}
