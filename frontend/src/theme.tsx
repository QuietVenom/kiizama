import {
  createSystem,
  defaultConfig,
  defineLayerStyles,
  defineTextStyles,
} from "@chakra-ui/react"
import { buttonRecipe } from "./theme/button.recipe"

const brandGradient =
  "linear-gradient(to right, var(--chakra-colors-ui-brand-gradient-start), var(--chakra-colors-ui-brand-gradient-end))"
const brandGradientHover =
  "linear-gradient(to right, var(--chakra-colors-ui-brand-gradient-start-hover), var(--chakra-colors-ui-brand-gradient-end-hover))"

const layerStyles = defineLayerStyles({
  publicPage: {
    value: {
      backgroundImage:
        "linear(to-b, {colors.ui.page}, {colors.ui.pageAccent} 48%, {colors.ui.panel})",
    },
  },
  publicGlowPrimary: {
    value: {
      borderRadius: "full",
      background: "ui.brandGlow",
      opacity: "0.5",
      filter: "blur(100px)",
    },
  },
  publicGlowSecondary: {
    value: {
      borderRadius: "full",
      background: "ui.brandGlowSoft",
      opacity: "0.8",
      filter: "blur(90px)",
    },
  },
  infoCard: {
    value: {
      background: "ui.panel",
      borderWidth: "1px",
      borderColor: "ui.borderSoft",
      borderRadius: "3xl",
      boxShadow: "ui.panel",
    },
  },
  dashboardCard: {
    value: {
      background: "ui.panel",
      borderWidth: "1px",
      borderColor: "ui.border",
      borderRadius: "4xl",
      boxShadow: "ui.card",
    },
  },
  dashboardCardInteractive: {
    value: {
      background: "ui.panel",
      borderWidth: "1px",
      borderColor: "ui.border",
      borderRadius: "3xl",
      boxShadow: "ui.card",
      transition: "transform 220ms ease, box-shadow 220ms ease",
      _hover: {
        transform: "translateY(-4px)",
        boxShadow: "ui.cardHover",
      },
    },
  },
  inverseCard: {
    value: {
      background: "ui.panelInverse",
      color: "ui.textInverse",
      borderRadius: "4xl",
      boxShadow: "ui.inverseCard",
    },
  },
  landingCard: {
    value: {
      background: "ui.panel",
      borderWidth: "1px",
      borderColor: "ui.borderSoft",
      borderRadius: "3xl",
      boxShadow: "ui.panelSm",
    },
  },
  navbarGlass: {
    value: {
      background: "ui.overlay",
      borderBottomWidth: "1px",
      borderBottomColor: "ui.border",
      backdropFilter: "blur(12px)",
    },
  },
  mobileMenu: {
    value: {
      background: "ui.panel",
      borderWidth: "1px",
      borderColor: "ui.border",
      borderRadius: "2xl",
      boxShadow: "ui.panelSm",
    },
  },
  pricingCard: {
    value: {
      background: "ui.panel",
      color: "ui.text",
      borderWidth: "1px",
      borderColor: "ui.borderSoft",
      borderRadius: "3xl",
      boxShadow: "ui.pricingCard",
    },
  },
  pricingCardHighlight: {
    value: {
      background: "ui.panelInverse",
      color: "ui.textInverse",
      borderWidth: "1px",
      borderColor: "ui.borderInverse",
      borderRadius: "3xl",
      boxShadow: "ui.pricingHighlight",
    },
  },
  faqCard: {
    value: {
      background: "ui.panel",
      borderWidth: "1px",
      borderColor: "ui.borderSoft",
      borderRadius: "2xl",
    },
  },
  faqCardActive: {
    value: {
      background: "ui.activeSoft",
      borderWidth: "1px",
      borderColor: "ui.brandBorderSoft",
      borderRadius: "2xl",
      boxShadow: "ui.panelSm",
    },
  },
  heroGlass: {
    value: {
      borderRadius: "4xl",
      background: "ui.overlaySoft",
      borderWidth: "1px",
      borderColor: "ui.glassBorder",
      boxShadow: "ui.heroGlass",
    },
  },
  heroAccentGlass: {
    value: {
      borderRadius: "4xl",
      background: "ui.accentGlass",
      borderWidth: "1px",
      borderColor: "ui.accentGlassBorder",
      boxShadow: "ui.heroAccentInset",
    },
  },
  heroMockCard: {
    value: {
      background: "ui.panel",
      borderWidth: "1px",
      borderColor: "ui.borderSoft",
      borderRadius: "3xl",
      boxShadow: "ui.heroCard",
    },
  },
  heroMockCardRaised: {
    value: {
      background: "ui.panel",
      borderWidth: "1px",
      borderColor: "ui.borderSoft",
      borderRadius: "3xl",
      boxShadow: "ui.heroCardRaised",
    },
  },
  cookiePanel: {
    value: {
      background: "ui.panel",
      borderTopWidth: "1px",
      borderColor: "ui.borderSoft",
      boxShadow: "ui.footerPanel",
    },
  },
  sectionMuted: {
    value: {
      background: "ui.panelAlt",
      borderTopWidth: "1px",
      borderBottomWidth: "1px",
      borderColor: "ui.borderSoft",
    },
  },
  sectionPattern: {
    value: {
      backgroundImage:
        "radial-gradient(circle, {colors.ui.patternDot} 1px, transparent 1px)",
      backgroundSize: "24px 24px",
      opacity: "0.5",
      pointerEvents: "none",
    },
  },
  brandGradientText: {
    value: {
      backgroundImage: brandGradient,
      backgroundClip: "text",
      color: "transparent",
    },
  },
  brandGradientBadge: {
    value: {
      backgroundImage: brandGradient,
      color: "ui.panel",
      boxShadow: "ui.brandButton",
    },
  },
  brandGradientButton: {
    value: {
      bg: "transparent",
      backgroundImage: brandGradient,
      color: "ui.panel",
      boxShadow: "ui.brandButton",
      transition: "all 220ms ease",
      _hover: {
        bg: "transparent",
        backgroundImage: brandGradientHover,
        transform: "translateY(-4px) scale(1.02)",
        boxShadow: "ui.brandButtonHover",
      },
    },
  },
})

const textStyles = defineTextStyles({
  eyebrow: {
    value: {
      color: "ui.link",
      textTransform: "uppercase",
      fontWeight: "bold",
      letterSpacing: "0.12em",
      fontSize: "xs",
    },
  },
  pageTitle: {
    value: {
      color: "ui.text",
      letterSpacing: "-0.02em",
      fontFamily:
        "'Plus Jakarta Sans', 'Avenir Next', 'Segoe UI', -apple-system, BlinkMacSystemFont, sans-serif",
    },
  },
  pageBody: {
    value: {
      color: "ui.secondaryText",
      lineHeight: "1.8",
    },
  },
})

export const system = createSystem(defaultConfig, {
  globalCss: {
    html: {
      fontSize: "16px",
      scrollBehavior: "smooth",
      bg: "ui.page",
    },
    body: {
      fontSize: "0.875rem",
      fontFamily:
        "'Plus Jakarta Sans', 'Avenir Next', 'Segoe UI', -apple-system, BlinkMacSystemFont, sans-serif",
      bg: "ui.page",
      color: "ui.text",
      margin: 0,
      padding: 0,
    },
    ".main-link": {
      color: "ui.link",
      fontWeight: "bold",
      textDecoration: "none",
      transition: "color 180ms ease",
      _hover: {
        color: "ui.mainHover",
      },
    },
    ".legal-link": {
      color: "ui.link",
      textDecoration: "underline",
      textUnderlineOffset: "0.14em",
      transition: "color 180ms ease",
      _hover: {
        color: "ui.mainHover",
      },
    },
  },
  theme: {
    tokens: {
      colors: {
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
        ui: {
          page: { value: { _light: "#FFFDF8", _dark: "#0B1120" } },
          pageAccent: { value: { _light: "#FFF9ED", _dark: "#10192A" } },
          panel: { value: { _light: "#FFFFFF", _dark: "#101828" } },
          panelAlt: { value: { _light: "#F8FAFC", _dark: "#172033" } },
          panelInverse: { value: { _light: "#18183B", _dark: "#060816" } },
          footer: { value: { _light: "#18183B", _dark: "#060816" } },
          text: { value: { _light: "#0F172A", _dark: "#F8FAFC" } },
          textInverse: { value: { _light: "#F8FAFC", _dark: "#F8FAFC" } },
          secondaryText: { value: { _light: "#64748B", _dark: "#CBD5E1" } },
          mutedText: { value: { _light: "#94A3B8", _dark: "#94A3B8" } },
          inverseMutedText: { value: { _light: "#CBD5E1", _dark: "#94A3B8" } },
          main: { value: { _light: "#F5C58E", _dark: "#F5C58E" } },
          mainHover: { value: { _light: "#EEB576", _dark: "#E6A964" } },
          link: { value: { _light: "#F97316", _dark: "#F5C58E" } },
          border: { value: { _light: "#F3E8D6", _dark: "#243047" } },
          borderSoft: { value: { _light: "#E8EDF5", _dark: "#1F2A3D" } },
          borderInverse: { value: { _light: "#FFFFFF33", _dark: "#243047" } },
          activeSoft: { value: { _light: "#FFF5E8", _dark: "#3A2A1B" } },
          contrast: { value: { _light: "#FFF9ED", _dark: "#10192A" } },
          soft: { value: { _light: "#E8EDF5", _dark: "#172033" } },
          surfaceSoft: { value: { _light: "#F8FAFC", _dark: "#172033" } },
          sidebarBorder: { value: { _light: "#F3E8D6", _dark: "#243047" } },
          ink: { value: { _light: "#0F172A", _dark: "#F8FAFC" } },
          infoSoft: { value: { _light: "#EBF3FF", _dark: "#10284A" } },
          infoText: { value: { _light: "#3B82F6", _dark: "#93C5FD" } },
          accentSoft: { value: { _light: "#F3E8FF", _dark: "#2C1B44" } },
          accentText: { value: { _light: "#9333EA", _dark: "#C084FC" } },
          successSoft: { value: { _light: "#E8F8EC", _dark: "#163425" } },
          successText: { value: { _light: "#22C55E", _dark: "#86EFAC" } },
          positiveSoft: { value: { _light: "#D1FAE5", _dark: "#143529" } },
          positiveText: { value: { _light: "#059669", _dark: "#6EE7B7" } },
          successStrongSoft: {
            value: { _light: "#D7F3E1", _dark: "#1C4D37" },
          },
          successStrongText: {
            value: { _light: "#15803D", _dark: "#86EFAC" },
          },
          roseSoft: { value: { _light: "#FCE7F3", _dark: "#47162E" } },
          roseText: { value: { _light: "#EC4899", _dark: "#F9A8D4" } },
          neutralSoft: { value: { _light: "#ECEFF5", _dark: "#1E293B" } },
          neutralText: { value: { _light: "#475569", _dark: "#CBD5E1" } },
          brandSoft: { value: { _light: "#FFF7EB", _dark: "#42210A" } },
          brandText: { value: { _light: "#F97316", _dark: "#F5C58E" } },
          brandBorderSoft: { value: { _light: "#FAD7AE", _dark: "#8B5D2B" } },
          brandGlow: { value: { _light: "#FDECD7", _dark: "#3A2A1B" } },
          brandGlowSoft: { value: { _light: "#FFF9ED", _dark: "#1A2436" } },
          danger: { value: { _light: "#EF4444", _dark: "#F87171" } },
          dangerSoft: { value: { _light: "#FEE2E2", _dark: "#451A1A" } },
          dangerText: { value: { _light: "#DC2626", _dark: "#FCA5A5" } },
          overlay: {
            value: {
              _light: "rgba(255, 255, 255, 0.84)",
              _dark: "rgba(11, 17, 32, 0.84)",
            },
          },
          overlaySoft: {
            value: {
              _light: "rgba(255, 255, 255, 0.62)",
              _dark: "rgba(16, 24, 40, 0.68)",
            },
          },
          overlayBackdrop: {
            value: {
              _light: "rgba(15, 23, 42, 0.30)",
              _dark: "rgba(2, 8, 23, 0.60)",
            },
          },
          glassBorder: {
            value: {
              _light: "rgba(255, 255, 255, 0.90)",
              _dark: "rgba(148, 163, 184, 0.18)",
            },
          },
          accentGlass: {
            value: {
              _light: "rgba(245, 197, 142, 0.16)",
              _dark: "rgba(245, 197, 142, 0.10)",
            },
          },
          accentGlassBorder: {
            value: {
              _light: "rgba(245, 197, 142, 0.38)",
              _dark: "rgba(245, 197, 142, 0.24)",
            },
          },
          inverseSoft: {
            value: {
              _light: "rgba(255, 255, 255, 0.06)",
              _dark: "rgba(255, 255, 255, 0.04)",
            },
          },
          inverseBorderSoft: {
            value: {
              _light: "rgba(255, 255, 255, 0.10)",
              _dark: "rgba(148, 163, 184, 0.15)",
            },
          },
          scrollbarThumb: { value: { _light: "#CBD5E1", _dark: "#475569" } },
          brandGradientStart: {
            value: { _light: "#ff7300", _dark: "#F5C58E" },
          },
          brandGradientEnd: {
            value: { _light: "#F59E0B", _dark: "#F59E0B" },
          },
          brandGradientStartHover: {
            value: { _light: "#F97316", _dark: "#EEB576" },
          },
          brandGradientEndHover: {
            value: { _light: "#D97706", _dark: "#E6A964" },
          },
          patternDot: {
            value: {
              _light: "rgba(148, 163, 184, 0.22)",
              _dark: "rgba(148, 163, 184, 0.12)",
            },
          },
        },
        design: {
          contrast: { value: { _light: "#18183B", _dark: "#0B1120" } },
          fg: { value: { _light: "#D97706", _dark: "#F5C58E" } },
          subtle: { value: { _light: "#FFF9ED", _dark: "#3A2A1B" } },
          muted: { value: { _light: "#FDECD7", _dark: "#4B3421" } },
          emphasized: { value: { _light: "#E6A964", _dark: "#EEB576" } },
          solid: { value: { _light: "#F5C58E", _dark: "#F5C58E" } },
          focusRing: { value: { _light: "#E6A964", _dark: "#F5C58E" } },
        },
      },
      shadows: {
        ui: {
          panel: {
            value: {
              _light: "0 16px 34px rgba(15, 23, 42, 0.06)",
              _dark: "0 18px 36px rgba(2, 8, 23, 0.42)",
            },
          },
          panelSm: {
            value: {
              _light: "0 12px 28px rgba(15, 23, 42, 0.06)",
              _dark: "0 14px 30px rgba(2, 8, 23, 0.34)",
            },
          },
          card: {
            value: {
              _light: "0 4px 20px rgba(15, 23, 42, 0.04)",
              _dark: "0 10px 24px rgba(2, 8, 23, 0.32)",
            },
          },
          cardHover: {
            value: {
              _light: "0 14px 30px rgba(15, 23, 42, 0.08)",
              _dark: "0 18px 30px rgba(2, 8, 23, 0.40)",
            },
          },
          inverseCard: {
            value: {
              _light: "0 14px 34px rgba(24, 24, 59, 0.18)",
              _dark: "0 18px 36px rgba(0, 0, 0, 0.50)",
            },
          },
          heroGlass: {
            value: {
              _light: "0 26px 62px rgba(15, 23, 42, 0.06)",
              _dark: "0 24px 56px rgba(2, 8, 23, 0.42)",
            },
          },
          heroAccentInset: {
            value: {
              _light: "inset 0 0 0 1px rgba(255, 255, 255, 0.50)",
              _dark: "inset 0 0 0 1px rgba(148, 163, 184, 0.12)",
            },
          },
          heroCard: {
            value: {
              _light: "0 20px 52px rgba(15, 23, 42, 0.10)",
              _dark: "0 18px 42px rgba(2, 8, 23, 0.38)",
            },
          },
          heroCardRaised: {
            value: {
              _light: "0 26px 58px rgba(15, 23, 42, 0.14)",
              _dark: "0 24px 52px rgba(2, 8, 23, 0.46)",
            },
          },
          pricingCard: {
            value: {
              _light: "0 12px 28px rgba(15, 23, 42, 0.06)",
              _dark: "0 14px 30px rgba(2, 8, 23, 0.34)",
            },
          },
          pricingHighlight: {
            value: {
              _light: "0 28px 56px rgba(24, 24, 59, 0.30)",
              _dark: "0 28px 56px rgba(0, 0, 0, 0.52)",
            },
          },
          brandButton: {
            value: {
              _light: "0 16px 34px rgba(245, 197, 142, 0.28)",
              _dark: "0 16px 34px rgba(245, 197, 142, 0.18)",
            },
          },
          brandButtonHover: {
            value: {
              _light: "0 18px 32px rgba(245, 158, 11, 0.35)",
              _dark: "0 18px 32px rgba(245, 158, 11, 0.25)",
            },
          },
          subtleButton: {
            value: {
              _light: "0 10px 20px rgba(15, 23, 42, 0.10)",
              _dark: "0 12px 24px rgba(2, 8, 23, 0.30)",
            },
          },
          footerPanel: {
            value: {
              _light: "0 -12px 30px rgba(0, 0, 0, 0.16)",
              _dark: "0 -12px 30px rgba(0, 0, 0, 0.38)",
            },
          },
        },
      },
    },
    textStyles,
    layerStyles,
    recipes: {
      button: buttonRecipe,
    },
  },
})
