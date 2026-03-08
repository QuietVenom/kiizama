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
        color: "ui.secondaryText",
        _hover: {
          bg: "ui.activeSoft",
          color: "ui.text",
        },
      },
    },
  },
})
