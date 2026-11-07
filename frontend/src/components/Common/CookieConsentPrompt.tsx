import { Stack, Text } from "@chakra-ui/react"
import { Link as RouterLink } from "@tanstack/react-router"
import { useEffect, useState } from "react"
import { Button } from "@/components/ui/button"
import {
  DialogBody,
  DialogContent,
  DialogFooter,
  DialogRoot,
  DialogTitle,
} from "@/components/ui/dialog"
import {
  type CookiePreferences,
  DEFAULT_COOKIE_PREFERENCES,
  readCookiePreferences,
  writeCookiePreferences,
} from "@/hooks/useCookieConsent"

const NECESSARY_ONLY_COOKIE_PREFERENCES: CookiePreferences = {
  strictlyNecessary: true,
  functional: false,
  analytics: false,
  marketing: false,
}

const CookieConsentPrompt = () => {
  const [isOpen, setIsOpen] = useState(false)

  useEffect(() => {
    if (!readCookiePreferences()) {
      setIsOpen(true)
    }
  }, [])

  const handleSavePreferences = (preferences: CookiePreferences) => {
    writeCookiePreferences(preferences)
    setIsOpen(false)
  }

  if (!isOpen) {
    return null
  }

  return (
    <DialogRoot
      open={isOpen}
      placement="center"
      closeOnEscape={false}
      closeOnInteractOutside={false}
    >
      <DialogContent
        maxW={{ base: "calc(100vw - 2rem)", md: "720px" }}
        w="full"
        rounded="3xl"
        borderWidth="1px"
        borderColor="ui.border"
        bg="ui.panel"
        boxShadow="ui.heroCardRaised"
        px={{ base: 6, md: 9 }}
        py={{ base: 7, md: 9 }}
      >
        <DialogBody p={0}>
          <Stack align="center" gap={5}>
            <Text textStyle="eyebrow" textAlign="center">
              Cookie Preferences
            </Text>
            <DialogTitle
              textAlign="center"
              fontSize={{ base: "3xl", md: "4xl" }}
              fontWeight="black"
              letterSpacing="-0.03em"
              lineHeight="0.95"
              maxW="12ch"
            >
              This website uses cookies
            </DialogTitle>
            <Text
              color="ui.secondaryText"
              fontSize={{ base: "md", md: "lg" }}
              lineHeight="1.9"
              textAlign="center"
              maxW="34ch"
            >
              We use cookies to keep the site working properly, improve your
              experience, and understand how visitors use Kiizama. You can allow
              all cookies or keep only strictly necessary cookies. You can
              change this later from Cookie Settings in the footer or read the{" "}
              <RouterLink to="/cookie-notice" className="main-link">
                Cookie Notice
              </RouterLink>
              .
            </Text>
          </Stack>
        </DialogBody>
        <DialogFooter
          p={0}
          flexDirection="column"
          mt={{ base: 7, md: 8 }}
          gap={3}
        >
          <Button
            w="full"
            size="lg"
            layerStyle="brandGradientButton"
            onClick={() => handleSavePreferences(DEFAULT_COOKIE_PREFERENCES)}
          >
            Allow all cookies
          </Button>
          <Button
            w="full"
            size="lg"
            variant="outline"
            onClick={() =>
              handleSavePreferences(NECESSARY_ONLY_COOKIE_PREFERENCES)
            }
          >
            Allow necessary cookies
          </Button>
        </DialogFooter>
      </DialogContent>
    </DialogRoot>
  )
}

export default CookieConsentPrompt
