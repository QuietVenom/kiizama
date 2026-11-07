import "@testing-library/jest-dom/vitest"

import { vi } from "vitest"

// Node >= 25 enables its own Web Storage globals by default. Without
// --localstorage-file its `localStorage` resolves to undefined and shadows the
// jsdom implementation, so tests fail on CI images using newer Node LTS.
// Always bind the storages from the jsdom window used by this environment.
const jsdomWindow = (
  globalThis as typeof globalThis & {
    jsdom?: { window: Window & typeof globalThis }
  }
).jsdom?.window

if (jsdomWindow) {
  for (const storage of ["localStorage", "sessionStorage"] as const) {
    Object.defineProperty(globalThis, storage, {
      configurable: true,
      writable: true,
      value: jsdomWindow[storage],
    })
  }
}

class ResizeObserverMock {
  observe = vi.fn()
  unobserve = vi.fn()
  disconnect = vi.fn()
}

Object.defineProperty(window, "matchMedia", {
  writable: true,
  value: vi.fn().mockImplementation((query: string) => ({
    matches: false,
    media: query,
    onchange: null,
    addEventListener: vi.fn(),
    removeEventListener: vi.fn(),
    addListener: vi.fn(),
    removeListener: vi.fn(),
    dispatchEvent: vi.fn(),
  })),
})

Object.defineProperty(window, "ResizeObserver", {
  writable: true,
  value: ResizeObserverMock,
})

Object.defineProperty(Element.prototype, "scrollIntoView", {
  writable: true,
  value: vi.fn(),
})
