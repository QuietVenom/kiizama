import i18n from "@/i18n"

import type { IgScrapeTerminalEventPayload } from "./types"

export const buildCompletedDescription = (
  payload: IgScrapeTerminalEventPayload,
) => {
  const requested = payload.counters.requested
  if (requested > 0) {
    const readyCount = payload.ready_usernames.length
    return i18n.t("creatorsSearch:toasts.completed.description", {
      readyCount,
      requestedCount: requested,
    })
  }

  return i18n.t("creatorsSearch:toasts.completed.fallback")
}
