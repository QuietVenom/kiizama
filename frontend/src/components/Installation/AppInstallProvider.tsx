import {
  createContext,
  type ReactNode,
  useContext,
  useEffect,
  useRef,
  useState,
} from "react"

interface InstallPromptEvent extends Event {
  prompt: () => Promise<void>
  userChoice: Promise<{ outcome: "accepted" | "dismissed" }>
}

type InstallResult = "idle" | "accepted" | "dismissed" | "unavailable"
type InstallState = {
  canInstall: boolean
  installed: boolean
  prompting: boolean
  result: InstallResult
  requestInstall: () => Promise<void>
}

const AppInstallContext = createContext<InstallState | null>(null)

export function AppInstallProvider({ children }: { children: ReactNode }) {
  const deferred = useRef<InstallPromptEvent | null>(null)
  const busy = useRef(false)
  const [canInstall, setCanInstall] = useState(false)
  const [installed, setInstalled] = useState(false)
  const [prompting, setPrompting] = useState(false)
  const [result, setResult] = useState<InstallResult>("idle")

  useEffect(() => {
    const displayMode = window.matchMedia("(display-mode: standalone)")
    const syncDisplayMode = () => {
      const standalone =
        displayMode.matches ||
        Boolean((navigator as Navigator & { standalone?: boolean }).standalone)
      setInstalled(standalone)
      if (standalone) {
        deferred.current = null
        setCanInstall(false)
      }
    }
    const onPrompt = (event: Event) => {
      // Only intercept an actual browser installation event.
      if (!("prompt" in event) || !("userChoice" in event)) return
      event.preventDefault()
      deferred.current = event as InstallPromptEvent
      setCanInstall(true)
      setResult("idle")
    }
    const onInstalled = () => {
      deferred.current = null
      setCanInstall(false)
      setInstalled(true)
      setResult("idle")
    }
    syncDisplayMode()
    displayMode.addEventListener("change", syncDisplayMode)
    window.addEventListener("beforeinstallprompt", onPrompt)
    window.addEventListener("appinstalled", onInstalled)
    return () => {
      displayMode.removeEventListener("change", syncDisplayMode)
      window.removeEventListener("beforeinstallprompt", onPrompt)
      window.removeEventListener("appinstalled", onInstalled)
    }
  }, [])

  const requestInstall = async () => {
    const event = deferred.current
    if (!event || busy.current || installed) return
    busy.current = true
    deferred.current = null
    setCanInstall(false)
    setPrompting(true)
    try {
      await event.prompt()
      const choice = await event.userChoice
      setResult(choice.outcome)
    } catch {
      setResult("unavailable")
    } finally {
      busy.current = false
      setPrompting(false)
    }
  }

  return (
    <AppInstallContext.Provider
      value={{ canInstall, installed, prompting, result, requestInstall }}
    >
      {children}
    </AppInstallContext.Provider>
  )
}

export function useAppInstall() {
  const state = useContext(AppInstallContext)
  if (!state) throw new Error("useAppInstall requires AppInstallProvider")
  return state
}
