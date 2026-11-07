import { Box, type BoxProps } from "@chakra-ui/react"

// Keep genuinely wide content accessible without making its page scroll sideways.
export function WideContent({ label, ...props }: BoxProps & { label: string }) {
  return (
    <Box
      {...props}
      role="region"
      aria-label={label}
      tabIndex={0}
      data-local-scroll="true"
      minW={0}
      maxW="full"
      overflowX="auto"
      _focusVisible={{
        outline: "2px solid",
        outlineColor: "ui.link",
        outlineOffset: "2px",
      }}
    />
  )
}
