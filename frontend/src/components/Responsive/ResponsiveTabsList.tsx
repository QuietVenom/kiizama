import { Box, Tabs } from "@chakra-ui/react"
import { useEffect, useRef } from "react"

function reveal(container: HTMLDivElement | null, element: HTMLElement) {
  if (!container) return
  const item = element.getBoundingClientRect()
  const bounds = container.getBoundingClientRect()
  if (item.left < bounds.left) container.scrollLeft -= bounds.left - item.left
  if (item.right > bounds.right)
    container.scrollLeft += item.right - bounds.right
}

export function ResponsiveTabsList({
  value,
  fitted = false,
  ...props
}: Tabs.ListProps & { value?: string; fitted?: boolean }) {
  const viewport = useRef<HTMLDivElement>(null)
  useEffect(() => {
    const selected = Array.from(
      viewport.current?.querySelectorAll<HTMLElement>('[role="tab"]') ?? [],
    ).find((tab) =>
      value
        ? tab.dataset.value === value
        : tab.getAttribute("aria-selected") === "true",
    )
    if (selected) reveal(viewport.current, selected)
  }, [value])
  return (
    <Box
      ref={viewport}
      minW={0}
      maxW="full"
      overflowX="auto"
      data-local-scroll="true"
    >
      <Tabs.List
        {...props}
        minW={fitted ? 0 : "max-content"}
        w={fitted ? "full" : props.w}
        css={
          fitted
            ? {
                ...props.css,
                "& > [role=tab]": {
                  flex: "1",
                  minWidth: 0,
                  whiteSpace: "normal",
                },
              }
            : props.css
        }
        onFocusCapture={(event) => {
          reveal(viewport.current, event.target as HTMLElement)
          props.onFocusCapture?.(event)
        }}
      />
    </Box>
  )
}
