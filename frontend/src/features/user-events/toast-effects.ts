import { toaster } from "@/components/ui/toaster"
import i18n from "@/i18n"
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
  payload.error || i18n.t("creatorsSearch:toasts.failed.fallback")

const createTerminalToast = (event: UserEvent) => {
  if (isIgScrapeJobCompletedEvent(event)) {
    toaster.create({
      title: i18n.t("creatorsSearch:toasts.completed.title"),
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
      title: i18n.t("creatorsSearch:toasts.failed.title"),
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
