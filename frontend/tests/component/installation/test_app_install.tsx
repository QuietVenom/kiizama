import { act, fireEvent, screen, waitFor, within } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import { useState } from "react"
import { beforeEach, describe, expect, test, vi } from "vitest"
import { useAppInstall } from "@/components/Installation/AppInstallProvider"
import InstallAppSettings from "@/components/Installation/InstallAppSettings"
import { renderWithProviders } from "../helpers/render"

function nativePrompt(
  prompt = vi.fn().mockResolvedValue(undefined),
  outcome: "accepted" | "dismissed" = "dismissed",
) {
  const event = new Event("beforeinstallprompt", { cancelable: true })
  Object.assign(event, { prompt, userChoice: Promise.resolve({ outcome }) })
  act(() => {
    window.dispatchEvent(event)
  })
  return { event, prompt }
}

// Both platform panels stay mounted; scope queries to the selected tab's panel
// so a panel that is still transitioning out cannot make queries ambiguous.
function activeGuide() {
  const selectedTab = screen.getByRole("tab", { selected: true })
  const panelId = selectedTab.getAttribute("aria-controls")
  const panel = panelId ? document.getElementById(panelId) : null
  if (!panel) throw new Error("Selected installation tab has no panel")
  return within(panel).getByRole("list")
}

function Probe() {
  const state = useAppInstall()
  return (
    <>
      <button
        type="button"
        disabled={!state.canInstall || state.prompting || state.installed}
        onClick={() => void state.requestInstall()}
      >
        Install
      </button>
      <output aria-label="result">{state.result}</output>
      <output aria-label="installed">{String(state.installed)}</output>
    </>
  )
}

describe("app installation", () => {
  beforeEach(() => {
    vi.mocked(window.matchMedia).mockImplementation((query) => ({
      matches: false,
      media: query,
      onchange: null,
      addEventListener: vi.fn(),
      removeEventListener: vi.fn(),
      addListener: vi.fn(),
      removeListener: vi.fn(),
      dispatchEvent: vi.fn(),
    }))
  })

  test.each(["es", "en", "pt-BR"] as const)(
    "manual guide is localized and usable without a native prompt: %s",
    async (language) => {
      const user = userEvent.setup()
      renderWithProviders(<InstallAppSettings />, { language })
      expect(activeGuide()).toBeVisible()
      expect(within(activeGuide()).getAllByRole("listitem")).toHaveLength(4)
      expect(screen.queryByRole("button")).not.toBeInTheDocument()
      await user.click(screen.getByRole("tab", { name: "iOS" }))
      await waitFor(() => expect(activeGuide()).toHaveAccessibleName(/iOS/))
      expect(within(activeGuide()).getAllByRole("listitem")).toHaveLength(4)
      expect(
        within(activeGuide()).getAllByText(/Safari/, { selector: "p" })[0],
      ).toBeVisible()
      expect(document.body.textContent).not.toContain("installation.ios.")
    },
  )

  test("native installation is requested only by the user and a dismissed event is consumed", async () => {
    renderWithProviders(<Probe />)
    expect(screen.getByRole("button")).toBeDisabled()
    const { event, prompt } = nativePrompt()
    expect(event.defaultPrevented).toBe(true)
    expect(prompt).not.toHaveBeenCalled()
    fireEvent.click(screen.getByRole("button"))
    await waitFor(() =>
      expect(screen.getByLabelText("result")).toHaveTextContent("dismissed"),
    )
    expect(screen.getByRole("button")).toBeDisabled()
    expect(prompt).toHaveBeenCalledTimes(1)
    expect(screen.getByLabelText("installed")).toHaveTextContent("false")
  })

  test("accepted request is not reported as installed until the browser confirms installation", async () => {
    renderWithProviders(<Probe />)
    nativePrompt(undefined, "accepted")
    fireEvent.click(screen.getByRole("button"))
    await waitFor(() =>
      expect(screen.getByLabelText("result")).toHaveTextContent("accepted"),
    )
    expect(screen.getByLabelText("installed")).toHaveTextContent("false")
    act(() => {
      window.dispatchEvent(new Event("appinstalled"))
    })
    expect(screen.getByLabelText("installed")).toHaveTextContent("true")
    expect(screen.getByRole("button")).toBeDisabled()
  })

  test("failed prompt retains manual guide and has no unhandled rejection", async () => {
    renderWithProviders(<InstallAppSettings />, { language: "en" })
    nativePrompt(
      vi.fn().mockRejectedValue(new Error("Browser rejected prompt")),
    )
    fireEvent.click(screen.getByRole("button", { name: "Install Kiizama" }))
    await waitFor(() =>
      expect(screen.getByRole("status")).toHaveTextContent(
        "could not start installation",
      ),
    )
    expect(activeGuide()).toBeVisible()
  })

  test("repeated clicks cannot invoke a pending prompt twice", async () => {
    renderWithProviders(<Probe />)
    let finish!: () => void
    const prompt = vi.fn(
      () =>
        new Promise<void>((resolve) => {
          finish = resolve
        }),
    )
    nativePrompt(prompt)
    fireEvent.click(screen.getByRole("button"))
    fireEvent.click(screen.getByRole("button"))
    expect(prompt).toHaveBeenCalledTimes(1)
    expect(screen.getByRole("button")).toBeDisabled()
    await act(async () => {
      finish()
    })
  })

  test("captured prompt survives changing route content under the shared provider", () => {
    function RouteSwitch() {
      const [show, setShow] = useState(false)
      return (
        <>
          <button type="button" onClick={() => setShow(true)}>
            Settings
          </button>
          {show && <Probe />}
        </>
      )
    }
    renderWithProviders(<RouteSwitch />)
    nativePrompt()
    fireEvent.click(screen.getByRole("button", { name: "Settings" }))
    expect(screen.getByRole("button", { name: "Install" })).toBeEnabled()
  })

  test("standalone launch shows installed state instead of installation instructions", () => {
    vi.mocked(window.matchMedia).mockImplementation((query) => ({
      matches: query === "(display-mode: standalone)",
      media: query,
      onchange: null,
      addEventListener: vi.fn(),
      removeEventListener: vi.fn(),
      addListener: vi.fn(),
      removeListener: vi.fn(),
      dispatchEvent: vi.fn(),
    }))
    renderWithProviders(<InstallAppSettings />, { language: "en" })
    expect(screen.getByRole("status")).toHaveTextContent("already installed")
    expect(screen.queryByRole("tab")).not.toBeInTheDocument()
  })
})
