import { Box, Button, HStack, Text } from "@chakra-ui/react"
import { useTranslation } from "react-i18next"
import { FiCheck, FiChevronDown, FiGlobe } from "react-icons/fi"
import {
  MenuContent,
  MenuItem,
  MenuRoot,
  MenuTrigger,
} from "@/components/ui/menu"
import type { SupportedLanguage } from "@/i18n"
import { normalizeLanguage, SUPPORTED_LANGUAGES } from "@/i18n"

type LanguageSwitcherVariant = "landing" | "dashboard" | "settings"

type LanguageOption = {
  value: SupportedLanguage
  label: string
}

type LanguageSwitcherProps = {
  variant?: LanguageSwitcherVariant
}

const triggerStyles: Record<
  LanguageSwitcherVariant,
  Record<string, unknown>
> = {
  landing: {
    h: 10,
    minW: "9.375rem",
    px: 4,
    rounded: "2xl",
    bg: "ui.text",
    color: "ui.panel",
    borderWidth: "1px",
    borderColor: "transparent",
    _hover: { bg: "ui.panelInverse" },
  },
  dashboard: {
    h: 10,
    minW: 0,
    px: 2,
    rounded: "2xl",
    bg: "ui.surfaceSoft",
    color: "ui.text",
    borderWidth: "1px",
    borderColor: "ui.sidebarBorder",
    _hover: { bg: "ui.panelAlt" },
  },
  settings: {
    h: 12,
    minW: 0,
    w: "min(100%, 15rem)",
    px: 4,
    rounded: "2xl",
    bg: "ui.surfaceSoft",
    color: "ui.text",
    borderWidth: "1px",
    borderColor: "ui.border",
    _hover: { bg: "ui.panelAlt" },
  },
}

export const LanguageSwitcher = ({
  variant = "landing",
}: LanguageSwitcherProps) => {
  const { i18n, t } = useTranslation("common")
  const activeLanguage = normalizeLanguage(
    i18n.resolvedLanguage ?? i18n.language,
  )
  const languageOptions: LanguageOption[] = [
    { value: "es", label: t("languageSwitcher.spanish") },
    { value: "pt-BR", label: t("languageSwitcher.portugueseBrazil") },
    { value: "en", label: t("languageSwitcher.english") },
  ]
  const activeOption =
    languageOptions.find((option) => option.value === activeLanguage) ??
    languageOptions[0]

  const availableOptions = languageOptions.filter((option) =>
    SUPPORTED_LANGUAGES.includes(option.value),
  )

  return (
    <MenuRoot positioning={{ placement: "bottom-end", gutter: 8 }}>
      <MenuTrigger asChild>
        <Button
          aria-label={t("languageSwitcher.select")}
          {...triggerStyles[variant]}
          title={activeOption.label}
          maxW="full"
          transition="background 180ms ease, border-color 180ms ease"
        >
          <HStack justify="space-between" w="full" gap={2}>
            <HStack gap={2} minW={0}>
              <Box
                as="span"
                display="inline-flex"
                alignItems="center"
                justifyContent="center"
                color="currentColor"
                fontSize="md"
              >
                <FiGlobe />
              </Box>
              <Text
                as="span"
                truncate
                fontWeight="medium"
                fontSize="sm"
                textAlign="left"
                display={variant === "dashboard" ? "none" : undefined}
                css={
                  variant === "dashboard"
                    ? {
                        "@container shell (min-width: 38rem)": {
                          display: "inline",
                        },
                      }
                    : undefined
                }
              >
                {activeOption.label}
              </Text>
              {variant === "dashboard" ? (
                <Text
                  as="span"
                  fontSize="xs"
                  fontWeight="bold"
                  aria-label={activeOption.label}
                  css={{
                    "@container shell (min-width: 38rem)": { display: "none" },
                  }}
                >
                  {activeLanguage === "pt-BR"
                    ? "PT"
                    : activeLanguage.toUpperCase()}
                </Text>
              ) : null}
            </HStack>
            <Box as="span" display="inline-flex" fontSize="md">
              <FiChevronDown />
            </Box>
          </HStack>
        </Button>
      </MenuTrigger>

      <MenuContent
        minW="min(15rem, calc(100vw - 1rem))"
        rounded="2xl"
        p={2}
        bg="ui.panelInverse"
        color="ui.textInverse"
        borderWidth="1px"
        borderColor="ui.borderInverse"
        boxShadow="ui.inverseCard"
      >
        {availableOptions.map((option) => {
          const isActive = option.value === activeLanguage

          return (
            <MenuItem
              key={option.value}
              value={option.value}
              closeOnSelect
              onClick={() => void i18n.changeLanguage(option.value)}
              rounded="xl"
              px={3}
              py={3}
              mb={1}
              cursor="pointer"
              bg={isActive ? "ui.panel" : "transparent"}
              color={isActive ? "ui.text" : "ui.textInverse"}
              _hover={{
                bg: isActive ? "ui.panel" : "whiteAlpha.200",
              }}
            >
              <HStack justify="space-between" w="full" gap={2}>
                <Text fontWeight={isActive ? "semibold" : "medium"}>
                  {option.label}
                </Text>
                {isActive ? <FiCheck /> : null}
              </HStack>
            </MenuItem>
          )
        })}
      </MenuContent>
    </MenuRoot>
  )
}

export default LanguageSwitcher
