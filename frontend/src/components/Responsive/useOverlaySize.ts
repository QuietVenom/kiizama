import { type BoxProps, useChakraContext } from "@chakra-ui/react"

// Clamp the requested size, resolving Chakra tokens and responsive values first.
// Width is capped without replacing a dialog's own desktop max-width recipe.
export function useOverlaySize() {
  const system = useChakraContext()
  const limit = (value: string | number | undefined, cap: string) => {
    if (
      value == null ||
      ["auto", "none", "fit-content", "max-content", "min-content"].includes(
        String(value),
      )
    )
      return cap
    const fallback = typeof value === "number" ? `${value}px` : value
    return `min(${system.token(`sizes.${value}`, fallback)}, ${cap})`
  }
  const clamp = (value: BoxProps["w"], cap: string): BoxProps["w"] => {
    if (value == null || typeof value === "string" || typeof value === "number")
      return limit(value, cap)
    if (Array.isArray(value))
      return value.map((item) =>
        item == null ? undefined : clamp(item, cap),
      ) as BoxProps["w"]
    return Object.fromEntries(
      Object.entries(value).map(([key, item]) => [key, clamp(item, cap)]),
    ) as BoxProps["w"]
  }
  return clamp
}
