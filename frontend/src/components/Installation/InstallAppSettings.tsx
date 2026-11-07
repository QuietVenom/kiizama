import {
  Box,
  Button,
  Container,
  Flex,
  Heading,
  Icon,
  Stack,
  Tabs,
  Text,
} from "@chakra-ui/react"
import { useState } from "react"
import { useTranslation } from "react-i18next"
import {
  FiCheckCircle,
  FiDownload,
  FiMoreVertical,
  FiPlusSquare,
  FiShare,
  FiSmartphone,
} from "react-icons/fi"
import { ResponsiveTabsList } from "@/components/Responsive/ResponsiveTabsList"
import { useAppInstall } from "./AppInstallProvider"

type Platform = "ios" | "android"
const initialPlatform = (): Platform =>
  /iPad|iPhone|iPod/.test(navigator.userAgent) ||
  (navigator.platform === "MacIntel" && navigator.maxTouchPoints > 1)
    ? "ios"
    : "android"

export default function InstallAppSettings() {
  const { t } = useTranslation("settings")
  const [platform, setPlatform] = useState<Platform>(initialPlatform)
  const { installed, canInstall, prompting, requestInstall, result } =
    useAppInstall()
  const stepIcons = [
    FiSmartphone,
    platform === "ios" ? FiShare : FiMoreVertical,
    FiPlusSquare,
    FiCheckCircle,
  ]

  return (
    <Container maxW="full" py={4}>
      <Stack gap={6} maxW="48rem" minW={0}>
        <Box>
          <Heading size="md">{t("installation.title")}</Heading>
          <Text mt={2} color="ui.secondaryText">
            {t("installation.description")}
          </Text>
          <Text mt={2} fontSize="sm" color="ui.secondaryText">
            {t("installation.online")}
          </Text>
        </Box>

        {installed ? (
          <Flex
            gap={3}
            p={4}
            rounded="xl"
            bg="ui.surfaceSoft"
            align="center"
            role="status"
          >
            <Icon
              as={FiCheckCircle}
              flexShrink={0}
              color="ui.link"
              boxSize={5}
            />
            <Text>{t("installation.installed")}</Text>
          </Flex>
        ) : (
          <>
            {(canInstall || prompting) && (
              <Button
                alignSelf="start"
                colorPalette="design"
                disabled={prompting}
                onClick={() => void requestInstall()}
              >
                <FiDownload />
                {t(
                  prompting ? "installation.prompting" : "installation.action",
                )}
              </Button>
            )}
            {result !== "idle" && (
              <Text role="status" color="ui.secondaryText" fontSize="sm">
                {t(`installation.result.${result}`)}
              </Text>
            )}
            <Tabs.Root
              value={platform}
              onValueChange={({ value }) => setPlatform(value as Platform)}
              variant="subtle"
            >
              <ResponsiveTabsList value={platform} fitted>
                <Tabs.Trigger value="ios">iOS</Tabs.Trigger>
                <Tabs.Trigger value="android">Android</Tabs.Trigger>
              </ResponsiveTabsList>
              {(["ios", "android"] as const).map((device) => (
                <Tabs.Content key={device} value={device} pt={5}>
                  <Stack
                    as="ol"
                    gap={4}
                    m={0}
                    p={0}
                    listStyleType="none"
                    aria-label={t("installation.stepsLabel", {
                      platform: device === "ios" ? "iOS" : "Android",
                    })}
                  >
                    {[1, 2, 3, 4].map((number, index) => (
                      <Flex
                        as="li"
                        key={number}
                        gap={3}
                        align="flex-start"
                        p={4}
                        borderWidth="1px"
                        borderColor="ui.border"
                        rounded="xl"
                        minW={0}
                      >
                        <Flex
                          boxSize={8}
                          flexShrink={0}
                          rounded="full"
                          bg="ui.activeSoft"
                          color="ui.link"
                          align="center"
                          justify="center"
                          fontWeight="bold"
                          aria-hidden="true"
                        >
                          {number}
                        </Flex>
                        <Box minW={0} flex="1">
                          <Flex align="center" gap={2} mb={1}>
                            <Icon
                              as={stepIcons[index]}
                              boxSize={4}
                              flexShrink={0}
                              color="ui.link"
                            />
                            <Text fontWeight="bold">
                              {t(`installation.${device}.step${number}.title`)}
                            </Text>
                          </Flex>
                          <Text fontSize="sm" color="ui.secondaryText">
                            {t(
                              `installation.${device}.step${number}.description`,
                            )}
                          </Text>
                        </Box>
                      </Flex>
                    ))}
                  </Stack>
                  <Text mt={4} fontSize="sm" color="ui.secondaryText">
                    {t(`installation.${device}.note`)}
                  </Text>
                </Tabs.Content>
              ))}
            </Tabs.Root>
          </>
        )}
      </Stack>
    </Container>
  )
}
