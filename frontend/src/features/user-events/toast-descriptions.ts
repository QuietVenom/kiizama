import type { IgScrapeTerminalEventPayload } from "./types"

export const buildCompletedDescription = (
  payload: IgScrapeTerminalEventPayload,
) => {
  const requested = payload.counters.requested
  if (requested > 0) {
    const readyCount = payload.ready_usernames.length
    return `${readyCount} of ${requested} usernames are ready.`
  }

  return "The Instagram scrape job completed successfully."
}
