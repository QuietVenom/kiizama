import {
  Box,
  Button,
  Link as ChakraLink,
  Container,
  chakra,
  Flex,
  Grid,
  HStack,
  Icon,
  SimpleGrid,
  Stack,
  Text,
} from "@chakra-ui/react"
import { Link } from "@tanstack/react-router"
import { useTranslation } from "react-i18next"
import { FaLinkedin } from "react-icons/fa"
import {
  cookieBackdropFadeIn,
  cookieBackdropFadeOut,
  cookiePanelSlideIn,
  cookiePanelSlideOut,
} from "@/components/Landing/cookieConsentAnimations"
import { Checkbox } from "@/components/ui/checkbox"
import {
  COOKIE_CONSENT_OPTIONS,
  useCookieConsent,
} from "@/hooks/useCookieConsent"

type FooterProps = {
  isWaitingListEnabled: boolean
}

const footerLinkStyles = {
  color: "ui.inverseMutedText",
  fontWeight: "medium",
  transition: "color 180ms ease",
  _hover: {
    color: "ui.main",
    textDecoration: "none",
  },
}

const Footer = (_props: FooterProps) => {
  const { t } = useTranslation("landing")
  const {
    cookiePreferences,
    isCookiePanelMounted,
    isCookiePanelVisible,
    cookiePanelAnimationMs,
    openCookiePanel,
    updateCookiePreference,
    acceptAllCookies,
    savePreferencesAndClose,
  } = useCookieConsent({ panelAnimationMs: 280 })

  return (
    <>
      <Box
        as="footer"
        bg="ui.footer"
        color="ui.textInverse"
        pt={{ base: 16, md: 20 }}
        pb={{ base: 10, md: 12 }}
        position="relative"
        overflow="hidden"
      >
        <Box
          position="absolute"
          top={0}
          left="50%"
          transform="translateX(-50%)"
          w={{ base: "85%", md: "760px" }}
          h="1px"
          bgGradient="linear(to-r, transparent, ui.brandGradientStart, transparent)"
          opacity={0.7}
        />

        <Container maxW="7xl">
          <Grid
            templateColumns={{
              base: "1fr",
              md: "1fr 1fr",
              lg: "1.1fr 1fr 1fr 1fr",
            }}
            gap={{ base: 10, md: 12 }}
            mb={{ base: 12, md: 16 }}
          >
            <Stack gap={7} align="flex-start">
              <HStack gap={3}>
                <chakra.img
                  src="/assets/images/noBgWhite.svg"
                  alt="Kiizama logo"
                  h={{ base: "10", md: "20" }}
                  w="auto"
                  display="block"
                  transform={{
                    base: "translateY(-5px)",
                    md: "translateY(-10px)",
                  }}
                />
              </HStack>

              <Text color="ui.inverseMutedText" maxW="xs" lineHeight="1.8">
                {t("footer.tagline")}
              </Text>

              <HStack gap={3}>
                <chakra.a
                  href="https://www.linkedin.com"
                  target="_blank"
                  rel="noopener noreferrer"
                  display="inline-flex"
                  alignItems="center"
                  justifyContent="center"
                  boxSize="10"
                  rounded="full"
                  bg="ui.inverseSoft"
                  color="ui.inverseMutedText"
                  transition="all 180ms ease"
                  _hover={{ bg: "ui.link", color: "ui.textInverse" }}
                >
                  <Icon as={FaLinkedin} boxSize={5} />
                </chakra.a>
                <chakra.a
                  href="/"
                  display="inline-flex"
                  alignItems="center"
                  justifyContent="center"
                  boxSize="10"
                  rounded="full"
                  bg="ui.inverseSoft"
                  color="ui.inverseMutedText"
                  fontWeight="bold"
                  fontSize="sm"
                  transition="all 180ms ease"
                  _hover={{ bg: "ui.link", color: "ui.textInverse" }}
                >
                  X
                </chakra.a>
              </HStack>
            </Stack>

            <Stack gap={4} align="flex-start">
              <Text
                fontSize="sm"
                fontWeight="bold"
                textTransform="uppercase"
                letterSpacing="0.08em"
              >
                {t("footer.sections.product")}
              </Text>
              <ChakraLink href="/#capabilities" {...footerLinkStyles}>
                {t("footer.links.capabilities")}
              </ChakraLink>
              <ChakraLink href="/#plans" {...footerLinkStyles}>
                {t("footer.links.pricing")}
              </ChakraLink>
              <ChakraLink href="/" {...footerLinkStyles}>
                {t("footer.links.apiDocs")}
              </ChakraLink>
              <ChakraLink href="/#faq" {...footerLinkStyles}>
                {t("footer.links.faq")}
              </ChakraLink>
            </Stack>

            <Stack gap={4} align="flex-start">
              <Text
                fontSize="sm"
                fontWeight="bold"
                textTransform="uppercase"
                letterSpacing="0.08em"
              >
                {t("footer.sections.company")}
              </Text>
              <Link to="/about-us">
                <Text
                  color="ui.inverseMutedText"
                  fontWeight="medium"
                  _hover={{ color: "ui.main" }}
                >
                  {t("footer.links.aboutUs")}
                </Text>
              </Link>
              <ChakraLink href="/" {...footerLinkStyles}>
                {t("footer.links.careers")}
              </ChakraLink>
              <ChakraLink href="/" {...footerLinkStyles}>
                {t("footer.links.contact")}
              </ChakraLink>
            </Stack>

            <Stack gap={4} align="flex-start">
              <Text
                fontSize="sm"
                fontWeight="bold"
                textTransform="uppercase"
                letterSpacing="0.08em"
              >
                {t("footer.sections.legal")}
              </Text>
              <Link to="/security">
                <Text
                  color="ui.inverseMutedText"
                  fontWeight="medium"
                  _hover={{ color: "ui.main" }}
                >
                  {t("footer.links.security")}
                </Text>
              </Link>
              <Link to="/privacy">
                <Text
                  color="ui.inverseMutedText"
                  fontWeight="medium"
                  _hover={{ color: "ui.main" }}
                >
                  {t("footer.links.privacyPolicy")}
                </Text>
              </Link>
              <Link to="/terms-conditions">
                <Text
                  color="ui.inverseMutedText"
                  fontWeight="medium"
                  _hover={{ color: "ui.main" }}
                >
                  {t("footer.links.termsOfService")}
                </Text>
              </Link>
              <Link to="/providers">
                <Text
                  color="ui.inverseMutedText"
                  fontWeight="medium"
                  _hover={{ color: "ui.main" }}
                >
                  {t("footer.links.providers")}
                </Text>
              </Link>
            </Stack>
          </Grid>

          <Flex
            pt={8}
            borderTopWidth="1px"
            borderTopColor="ui.inverseBorderSoft"
            direction={{ base: "column", md: "row" }}
            justify="space-between"
            align={{ base: "flex-start", md: "center" }}
            gap={4}
          >
            <Text color="ui.inverseMutedText" fontSize="sm">
              {t("footer.copyright", { year: new Date().getFullYear() })}
            </Text>
            <Button
              variant="ghost"
              px={0}
              h="auto"
              color="ui.inverseMutedText"
              _hover={{ bg: "transparent", color: "ui.textInverse" }}
              onClick={openCookiePanel}
            >
              {t("footer.cookieSettings")}
            </Button>
          </Flex>
        </Container>
      </Box>

      {isCookiePanelMounted && (
        <Box
          position="fixed"
          inset={0}
          zIndex="overlay"
          pointerEvents={isCookiePanelVisible ? "auto" : "none"}
        >
          <Box
            position="absolute"
            inset={0}
            bg="ui.overlayBackdrop"
            animation={`${isCookiePanelVisible ? cookieBackdropFadeIn : cookieBackdropFadeOut} ${cookiePanelAnimationMs}ms ease forwards`}
          />
          <Box
            position="absolute"
            bottom={0}
            insetX={0}
            layerStyle="cookiePanel"
            px={{ base: 4, md: 6 }}
            py={{ base: 4, md: 5 }}
            transformOrigin="bottom center"
            animation={`${isCookiePanelVisible ? cookiePanelSlideIn : cookiePanelSlideOut} ${cookiePanelAnimationMs}ms cubic-bezier(0.22, 1, 0.36, 1) forwards`}
          >
            <Stack gap={4}>
              <Flex justify="flex-end">
                <Button size="sm" onClick={savePreferencesAndClose}>
                  {t("footer.cookiePanel.done")}
                </Button>
              </Flex>

              <Stack gap={1} align="center">
                <Text textAlign="center" fontSize={{ base: "md", md: "lg" }}>
                  {t("footer.cookiePanel.title")}
                </Text>
                <Text
                  textAlign="center"
                  color="ui.secondaryText"
                  fontSize={{ base: "sm", md: "md" }}
                  maxW="4xl"
                >
                  {t("footer.cookiePanel.description")}
                </Text>
              </Stack>

              <SimpleGrid columns={{ base: 1, md: 2, lg: 4 }} gap={3}>
                {COOKIE_CONSENT_OPTIONS.map((option) => (
                  <HStack
                    key={option.key}
                    justify="space-between"
                    borderWidth="1px"
                    borderColor="ui.borderSoft"
                    rounded="xl"
                    px={4}
                    py={3}
                  >
                    <Text color="ui.text" fontWeight="medium">
                      {t(`footer.cookiePanel.options.${option.key}`)}
                    </Text>
                    <Checkbox
                      checked={cookiePreferences[option.key]}
                      disabled={!option.editable}
                      aria-label={t("footer.cookiePanel.aria.cookies", {
                        label: t(`footer.cookiePanel.options.${option.key}`),
                      })}
                      onCheckedChange={({ checked }) => {
                        if (option.key === "strictlyNecessary") {
                          return
                        }
                        updateCookiePreference(option.key, checked)
                      }}
                    />
                  </HStack>
                ))}
              </SimpleGrid>

              <Stack gap={1} align="center">
                <Button variant="outline" onClick={acceptAllCookies}>
                  {t("footer.cookiePanel.acceptAll")}
                </Button>
                <Link to="/cookie-notice" className="legal-link">
                  {t("footer.cookiePanel.details")}
                </Link>
              </Stack>
            </Stack>
          </Box>
        </Box>
      )}
    </>
  )
}

export default Footer
