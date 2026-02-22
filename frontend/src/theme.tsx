import { createSystem, defaultConfig } from "@chakra-ui/react"
import { buttonRecipe } from "./theme/button.recipe"

export const system = createSystem(defaultConfig, {
  globalCss: {
    html: {
      fontSize: "16px",
      scrollBehavior: "smooth",
    },
    body: {
      fontSize: "0.875rem",
      fontFamily:
        "'Plus Jakarta Sans', 'Avenir Next', 'Segoe UI', -apple-system, BlinkMacSystemFont, sans-serif",
      bg: "#FFFDF8",
      color: "#0F172A",
      margin: 0,
      padding: 0,
    },
    ".main-link": {
      color: "ui.main",
      fontWeight: "bold",
    },
  },
  theme: {
    tokens: {
      colors: {
        ui: {
          main: { value: "#F5C58E" },
          footer: { value: "#18183B" },
          soft: { value: "#E8EEF7" },
          contrast: { value: "#FFF9ED" },
          ink: { value: "#0F172A" },
          page: { value: "#FFFDF8" },
          sidebarBorder: { value: "#F3E8D6" },
          surfaceSoft: { value: "#F8FAFC" },
          activeSoft: { value: "#FFF5E8" },
          secondaryText: { value: "#64748B" },
          mutedText: { value: "#94A3B8" },
        },
        design: {
          "50": { value: "#FFFDF8" },
          "100": { value: "#FDECD7" },
          "200": { value: "#F9D7AE" },
          "500": { value: "#F5C58E" },
          "600": { value: "#E6A964" },
        },
      },
    },
    semanticTokens: {
      colors: {
        design: {
          contrast: { value: "#18183B" },
          fg: { value: "#E6A964" },
          subtle: { value: "#FFF9ED" },
          muted: { value: "#FDECD7" },
          emphasized: { value: "#E6A964" },
          solid: { value: "#F5C58E" },
          focusRing: { value: "#F5C58E" },
        },
      },
    },
    recipes: {
      button: buttonRecipe,
    },
  },
})
