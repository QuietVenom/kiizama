import { describe, expect, test } from "vitest"

import type {
  ProfileSnapshotExpanded,
  ProfileSnapshotExpandedCollection,
} from "../../../../src/client"
import {
  getReadyUsernamesFromSearchResult,
  getValidationMessage,
  sortSnapshotsByUsernames,
} from "../../../../src/routes/_layout/-components/creators-search/creators-search.logic"

const createSnapshot = (username: string): ProfileSnapshotExpanded =>
  ({
    profile: {
      username,
    },
    profile_id: `profile-${username}`,
    scraped_at: "2026-01-01T00:00:00Z",
  }) as ProfileSnapshotExpanded

describe("creators search logic", () => {
  test("creators_search_logic_ready_usernames_excludes_expired_and_missing", () => {
    // Arrange
    const result: ProfileSnapshotExpandedCollection = {
      expired_usernames: ["expired_creator"],
      missing_usernames: ["missing_creator"],
      snapshots: [
        createSnapshot("ready_creator"),
        createSnapshot("expired_creator"),
      ],
    }

    // Act
    const readyUsernames = getReadyUsernamesFromSearchResult(
      ["ready_creator", "expired_creator", "missing_creator"],
      result,
    )

    // Assert
    expect(readyUsernames).toEqual(["ready_creator"])
  })

  test("creators_search_logic_snapshots_sort_by_submitted_usernames", () => {
    // Arrange
    const alphaSnapshot = createSnapshot("alpha")
    const betaSnapshot = createSnapshot("beta")
    const unmatchedSnapshot = createSnapshot("unmatched")

    // Act
    const sortedSnapshots = sortSnapshotsByUsernames(
      [unmatchedSnapshot, alphaSnapshot, betaSnapshot],
      ["beta", "alpha"],
    )

    // Assert
    expect(sortedSnapshots).toEqual([
      betaSnapshot,
      alphaSnapshot,
      unmatchedSnapshot,
    ])
  })

  test("creators_search_logic_validation_message_reports_invalid_usernames", () => {
    // Arrange / Act
    const message = getValidationMessage(["InvalidName"], false)

    // Assert
    expect(message).toContain("Invalid usernames: @InvalidName")
    expect(message).toContain("lowercase letters")
  })

  test("creators_search_logic_validation_message_reports_overflow", () => {
    // Arrange / Act / Assert
    expect(getValidationMessage([], true)).toBe(
      "You can search up to 50 usernames per request.",
    )
  })
})
