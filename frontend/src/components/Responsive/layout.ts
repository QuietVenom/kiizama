// These policies use the space left inside a page/dialog, not a device model.
export const boundedContent = {
  minW: 0,
  maxW: "full",
  overflowWrap: "anywhere",
} as const

export const fluidColumns = (minimum = "16rem") =>
  `repeat(auto-fit, minmax(min(100%, ${minimum}), 1fr))`

// The content region is a named container so sidebar width is already accounted for.
export const formSummaryLayout = {
  gridTemplateColumns: "minmax(0, 1fr)",
  "@container page (min-width: 58rem)": {
    gridTemplateColumns: "minmax(0, 1.65fr) minmax(0, 22.5rem)",
  },
} as const

export const overlayBounds = {
  maxWidth:
    "calc(100vw - max(1rem, env(safe-area-inset-left) + env(safe-area-inset-right)))",
  maxHeight:
    "calc(100dvh - max(1rem, env(safe-area-inset-top) + env(safe-area-inset-bottom)))",
  minWidth: 0,
  overflowWrap: "anywhere",
} as const
