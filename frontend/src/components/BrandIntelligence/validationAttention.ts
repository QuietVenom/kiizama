export const validationAttentionCss = {
  borderColor: "ui.danger",
  color: "ui.dangerText",
  animation: "validation-attention-pulse 1.8s ease-in-out infinite",
  "@keyframes validation-attention-pulse": {
    "0%": {
      boxShadow: "0 0 0 0 color-mix(in srgb, currentcolor 45%, transparent)",
    },
    "70%": {
      boxShadow: "0 0 0 10px transparent",
    },
    "100%": {
      boxShadow: "0 0 0 0 transparent",
    },
  },
  "@media (prefers-reduced-motion: reduce)": {
    animation: "none",
  },
} as const
