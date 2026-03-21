import { toaster } from "@/components/ui/toaster"
import { registerUserEventEffect } from "./effects"
import { buildCompletedDescription } from "./toast-descriptions"
import {
  type IgScrapeTerminalEventPayload,
  isIgScrapeJobCompletedEvent,
  isIgScrapeJobFailedEvent,
  type UserEvent,
} from "./types"

const TERMINAL_TOAST_DURATION_MS = 7000

const buildFailedDescription = (payload: IgScrapeTerminalEventPayload) =>
  payload.error || "The Instagram scrape job failed."

const createTerminalToast = (event: UserEvent) => {
  if (isIgScrapeJobCompletedEvent(event)) {
    toaster.create({
      title: "Scrape completed",
      description: buildCompletedDescription(event.envelope.payload),
      duration: TERMINAL_TOAST_DURATION_MS,
      type: "success",
      meta: {
        closable: true,
      },
    })
    return
  }

  if (isIgScrapeJobFailedEvent(event)) {
    toaster.create({
      title: "Scrape failed",
      description: buildFailedDescription(event.envelope.payload),
      duration: TERMINAL_TOAST_DURATION_MS,
      type: "error",
      meta: {
        closable: true,
      },
    })
  }
}

export const registerToastUserEventEffects = () =>
  registerUserEventEffect(createTerminalToast)
