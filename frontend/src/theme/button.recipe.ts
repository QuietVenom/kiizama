import { defineRecipe } from "@chakra-ui/react"

export const buttonRecipe = defineRecipe({
  base: {
    fontWeight: "bold",
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
    colorPalette: "design",
  },
  variants: {
    variant: {
      ghost: {
        bg: "transparent",
        _hover: {
          bg: "ui.contrast",
        },
      },
    },
  },
})
