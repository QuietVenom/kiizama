import { toaster } from "@/components/ui/toaster"
import i18n from "@/i18n"

export const SEARCH_STARTED_TOAST_DURATION_MS = 7000

export const showSearchStartedToast = ({
  jobCount,
  profileCount,
}: {
  jobCount: number
  profileCount: number
}) => {
  toaster.create({
    title: i18n.t("creatorsSearch:toasts.started.title"),
    description: i18n.t("creatorsSearch:toasts.started.description", {
      profiles: i18n.t("creatorsSearch:toasts.started.profiles", {
        count: profileCount,
      }),
      jobs: i18n.t("creatorsSearch:toasts.started.jobs", {
        count: jobCount,
      }),
    }),
    duration: SEARCH_STARTED_TOAST_DURATION_MS,
    type: "info",
    meta: {
      closable: true,
    },
  })
}
