import { Box, Button, HStack, Text } from "@chakra-ui/react"
import { useMemo } from "react"
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
    h: 12,
    minW: "10.9375rem",
    px: 4,
    rounded: "2xl",
    bg: "ui.surfaceSoft",
    color: "ui.text",
    borderWidth: "1px",
    borderColor: "ui.sidebarBorder",
    _hover: { bg: "ui.panelAlt" },
  },
  settings: {
    h: 12,
    minW: "15rem",
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
    { value: "en", label: t("languageSwitcher.english") },
    { value: "es", label: t("languageSwitcher.spanish") },
    { value: "pt-BR", label: t("languageSwitcher.portugueseBrazil") },
  ]
  const activeOption =
    languageOptions.find((option) => option.value === activeLanguage) ??
    languageOptions[0]

  const availableOptions = useMemo(
    () =>
      languageOptions.filter((option) =>
        SUPPORTED_LANGUAGES.includes(option.value),
      ),
    [languageOptions.filter],
  )

  return (
    <MenuRoot positioning={{ placement: "bottom-end", gutter: 8 }}>
      <MenuTrigger asChild>
        <Button
          aria-label={t("languageSwitcher.select")}
          {...triggerStyles[variant]}
          transition="background 180ms ease, border-color 180ms ease"
        >
          <HStack justify="space-between" w="full" gap={3}>
            <HStack gap={3} minW={0}>
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
              >
                {activeOption.label}
              </Text>
            </HStack>
            <Box as="span" display="inline-flex" fontSize="md">
              <FiChevronDown />
            </Box>
          </HStack>
        </Button>
      </MenuTrigger>

      <MenuContent
        minW={triggerStyles[variant].minW as string}
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
              <HStack justify="space-between" w="full" gap={3}>
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
