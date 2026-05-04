import { Container, Heading, Stack, Text } from "@chakra-ui/react"
import { useTheme } from "next-themes"
import { useTranslation } from "react-i18next"

import LanguageSwitcher from "@/components/Common/LanguageSwitcher"
import { Radio, RadioGroup } from "@/components/ui/radio"

const Appearance = () => {
  const { t } = useTranslation("common")
  const { theme, setTheme } = useTheme()

  return (
    <Container maxW="full">
      <Heading size="sm" py={4}>
        {t("navigation.appearance")}
      </Heading>

      <Stack gap={3} mb={8}>
        <Text fontSize="sm" fontWeight="semibold">
          {t("labels.language")}
        </Text>
        <LanguageSwitcher variant="settings" />
      </Stack>

      <RadioGroup
        onValueChange={(e) => setTheme(e.value ?? "system")}
        value={theme}
        colorPalette="design"
      >
        <Stack>
          <Radio value="system">{t("theme.system")}</Radio>
          <Radio value="light">{t("theme.lightMode")}</Radio>
          <Radio value="dark">{t("theme.darkMode")}</Radio>
        </Stack>
      </RadioGroup>
    </Container>
  )
}
export default Appearance
