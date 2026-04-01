import {
  Box,
  Link as ChakraLink,
  ClientOnly,
  Container,
  HStack,
  IconButton,
  Skeleton,
  Stack,
} from "@chakra-ui/react"
import { Link } from "@tanstack/react-router"
import type { RefObject } from "react"
import { useState } from "react"
import { CiDark, CiLight } from "react-icons/ci"
import { FiMenu, FiX } from "react-icons/fi"
import ThemeLogo from "@/components/Common/ThemeLogo"
import { Button } from "@/components/ui/button"
import { useColorMode } from "@/components/ui/color-mode"

type SectionKey = "home" | "features" | "pricing" | "faq"

const sectionLinks: { href: string; key: SectionKey; label: string }[] = [
  { key: "home", label: "Home", href: "/" },
  { key: "features", label: "Capabilities", href: "/#capabilities" },
  { key: "pricing", label: "Plans", href: "/#plans" },
  { key: "faq", label: "FAQ", href: "/#faq" },
]

const MOBILE_MENU_ANIMATION_MS = 320

const getHeaderOffset = (navbarRef: RefObject<HTMLElement | null>) => {
  const header = navbarRef.current
  return header ? header.getBoundingClientRect().height : 0
}

const scrollToSection = (
  sectionRef: RefObject<HTMLElement | null>,
  navbarRef: RefObject<HTMLElement | null>,
) => {
  const section = sectionRef.current
  if (!section) return
  const headerOffset = getHeaderOffset(navbarRef)
  const sectionTop = section.getBoundingClientRect().top + window.scrollY
  const top = Math.max(0, sectionTop - headerOffset - 4)
  window.scrollTo({ top, behavior: "smooth" })
}

const LandingThemeToggleButton = () => {
  const { colorMode, toggleColorMode } = useColorMode()
  const isDarkMode = colorMode === "dark"

  return (
    <ClientOnly fallback={<Skeleton boxSize="10" rounded="full" />}>
      <IconButton
        aria-label={isDarkMode ? "Switch to light mode" : "Switch to dark mode"}
        onClick={toggleColorMode}
        variant="ghost"
        rounded="full"
        boxSize="10"
        bg="ui.panel"
        color="ui.text"
        borderWidth="1px"
        borderColor="ui.border"
        _hover={{ bg: "ui.panelAlt", color: "ui.link" }}
      >
        <Box as="span" display="inline-flex" fontSize="1.35rem">
          {isDarkMode ? <CiLight /> : <CiDark />}
        </Box>
      </IconButton>
    </ClientOnly>
  )
}

type LandingNavbarProps = {
  isWaitingListEnabled: boolean
  navbarRef: RefObject<HTMLElement | null>
  sectionRefs?: Partial<Record<SectionKey, RefObject<HTMLElement | null>>>
}

const LandingNavbar = ({
  isWaitingListEnabled,
  navbarRef,
  sectionRefs,
}: LandingNavbarProps) => {
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false)
  const loginUrl = "/login"
  const blogUrl = "/blog"

  const handleSectionClick = (key: SectionKey) => {
    const targetSection = sectionRefs?.[key]
    if (!targetSection) return

    if (mobileMenuOpen) {
      setMobileMenuOpen(false)
      window.setTimeout(() => {
        scrollToSection(targetSection, navbarRef)
      }, MOBILE_MENU_ANIMATION_MS)
      return
    }
    scrollToSection(targetSection, navbarRef)
  }

  return (
    <Box
      ref={navbarRef}
      as="header"
      position="sticky"
      top={0}
      zIndex="docked"
      layerStyle="navbarGlass"
    >
      <Container maxW="full" py={4} px={{ base: 4, md: 8, lg: 12 }}>
        <Box
          display="grid"
          gridTemplateColumns={{ base: "1fr auto", md: "1fr auto 1fr" }}
          alignItems="center"
          w="full"
          gap={{ base: 2, md: 8 }}
        >
          <ChakraLink
            href="/"
            aria-label="Refresh landing page"
            _hover={{ textDecoration: "none" }}
            display="inline-flex"
            alignItems="center"
            justifySelf="start"
          >
            <HStack gap={3} align="center">
              <ThemeLogo
                h={{ base: "10", sm: "12" }}
                w="auto"
                display="block"
                transform={{ base: "translateY(-5px)", sm: "translateY(-6px)" }}
              />
            </HStack>
          </ChakraLink>

          <HStack
            gap={2}
            justifySelf="center"
            display={{ base: "none", md: "flex" }}
          >
            {sectionLinks.map((link) =>
              sectionRefs?.[link.key] ? (
                <Button
                  key={link.key}
                  variant="ghost"
                  color={link.key === "home" ? "ui.text" : "ui.secondaryText"}
                  fontWeight={link.key === "home" ? "semibold" : "medium"}
                  fontSize="sm"
                  px={3}
                  h={10}
                  _hover={{ color: "ui.link", bg: "transparent" }}
                  onClick={() => handleSectionClick(link.key)}
                >
                  {link.label}
                </Button>
              ) : (
                <ChakraLink
                  key={link.key}
                  href={link.href}
                  _hover={{ textDecoration: "none" }}
                >
                  <Button
                    variant="ghost"
                    color={link.key === "home" ? "ui.text" : "ui.secondaryText"}
                    fontWeight={link.key === "home" ? "semibold" : "medium"}
                    fontSize="sm"
                    px={3}
                    h={10}
                    _hover={{ color: "ui.link", bg: "transparent" }}
                  >
                    {link.label}
                  </Button>
                </ChakraLink>
              ),
            )}
            <Link to={blogUrl}>
              <Button
                variant="ghost"
                color="ui.secondaryText"
                fontWeight="medium"
                fontSize="sm"
                px={3}
                h={10}
                _hover={{ color: "ui.link", bg: "transparent" }}
              >
                Blog
              </Button>
            </Link>
          </HStack>

          <HStack
            gap={2}
            justifySelf={{ base: "auto", md: "end" }}
            display={{ base: "none", md: "flex" }}
          >
            <LandingThemeToggleButton />
            <ChakraLink href={loginUrl} _hover={{ textDecoration: "none" }}>
              <Button
                variant="ghost"
                color="ui.secondaryText"
                fontWeight="semibold"
                _hover={{ bg: "transparent", color: "ui.text" }}
              >
                Log In
              </Button>
            </ChakraLink>
            {isWaitingListEnabled ? (
              <Link to="/waiting-list">
                <Button
                  rounded="full"
                  px={6}
                  h={11}
                  bg="ui.text"
                  color="ui.panel"
                  _hover={{ bg: "ui.panelInverse" }}
                >
                  Waiting List
                </Button>
              </Link>
            ) : (
              <Link to="/signup">
                <Button
                  rounded="full"
                  px={6}
                  h={11}
                  bg="ui.text"
                  color="ui.panel"
                  _hover={{ bg: "ui.panelInverse" }}
                >
                  Sign Up
                </Button>
              </Link>
            )}
          </HStack>

          <IconButton
            display={{ base: "inline-flex", md: "none" }}
            aria-label={mobileMenuOpen ? "Close menu" : "Open menu"}
            variant="ghost"
            color="ui.text"
            onClick={() => setMobileMenuOpen((open) => !open)}
          >
            <Box position="relative" boxSize="5">
              <Box
                position="absolute"
                inset={0}
                display="inline-flex"
                alignItems="center"
                justifyContent="center"
                transition="opacity 180ms ease, transform 220ms ease"
                opacity={mobileMenuOpen ? 0 : 1}
                transform={
                  mobileMenuOpen
                    ? "rotate(-90deg) scale(0.8)"
                    : "rotate(0deg) scale(1)"
                }
              >
                <FiMenu />
              </Box>
              <Box
                position="absolute"
                inset={0}
                display="inline-flex"
                alignItems="center"
                justifyContent="center"
                transition="opacity 180ms ease, transform 220ms ease"
                opacity={mobileMenuOpen ? 1 : 0}
                transform={
                  mobileMenuOpen
                    ? "rotate(0deg) scale(1)"
                    : "rotate(90deg) scale(0.8)"
                }
              >
                <FiX />
              </Box>
            </Box>
          </IconButton>
        </Box>

        <Box
          display={{ base: "block", md: "none" }}
          mt={mobileMenuOpen ? 3 : 0}
          borderWidth={mobileMenuOpen ? "1px" : "0"}
          borderColor={mobileMenuOpen ? "ui.border" : "transparent"}
          rounded="2xl"
          bg="ui.panel"
          boxShadow={mobileMenuOpen ? "ui.panelSm" : "none"}
          overflow="hidden"
          maxH={mobileMenuOpen ? "420px" : "0px"}
          opacity={mobileMenuOpen ? 1 : 0}
          transform={mobileMenuOpen ? "translateY(0)" : "translateY(-8px)"}
          transition="max-height 280ms ease, opacity 220ms ease, transform 280ms ease, margin 280ms ease"
          pointerEvents={mobileMenuOpen ? "auto" : "none"}
        >
          <Stack gap={0}>
            {sectionLinks.map((link) =>
              sectionRefs?.[link.key] ? (
                <Button
                  key={link.key}
                  variant="ghost"
                  justifyContent="flex-start"
                  borderRadius={0}
                  h="12"
                  borderBottomWidth="1px"
                  borderBottomColor="ui.border"
                  color={link.key === "home" ? "ui.text" : "ui.secondaryText"}
                  fontWeight={link.key === "home" ? "semibold" : "medium"}
                  onClick={() => handleSectionClick(link.key)}
                >
                  {link.label}
                </Button>
              ) : (
                <ChakraLink
                  key={link.key}
                  href={link.href}
                  onClick={() => setMobileMenuOpen(false)}
                  _hover={{ textDecoration: "none" }}
                >
                  <Button
                    variant="ghost"
                    justifyContent="flex-start"
                    borderRadius={0}
                    h="12"
                    w="full"
                    borderBottomWidth="1px"
                    borderBottomColor="ui.border"
                    color={link.key === "home" ? "ui.text" : "ui.secondaryText"}
                    fontWeight={link.key === "home" ? "semibold" : "medium"}
                  >
                    {link.label}
                  </Button>
                </ChakraLink>
              ),
            )}
            <Link to={blogUrl} onClick={() => setMobileMenuOpen(false)}>
              <Button
                variant="ghost"
                justifyContent="flex-start"
                borderRadius={0}
                h="12"
                w="full"
                color="ui.secondaryText"
                borderBottomWidth="1px"
                borderBottomColor="ui.border"
              >
                Blog
              </Button>
            </Link>
            <Box
              px={3}
              py={3}
              borderBottomWidth="1px"
              borderBottomColor="ui.border"
            >
              <LandingThemeToggleButton />
            </Box>
            <ChakraLink
              href={loginUrl}
              onClick={() => setMobileMenuOpen(false)}
              _hover={{ textDecoration: "none" }}
            >
              <Button
                variant="ghost"
                justifyContent="flex-start"
                borderRadius={0}
                h="12"
                w="full"
                color="ui.secondaryText"
                borderBottomWidth="1px"
                borderBottomColor="ui.border"
              >
                Log In
              </Button>
            </ChakraLink>
            <Box p={3}>
              {isWaitingListEnabled ? (
                <Link
                  to="/waiting-list"
                  onClick={() => setMobileMenuOpen(false)}
                >
                  <Button
                    w="full"
                    h={11}
                    rounded="xl"
                    bg="ui.text"
                    color="ui.panel"
                    _hover={{ bg: "ui.panelInverse" }}
                  >
                    Waiting List
                  </Button>
                </Link>
              ) : (
                <Link to="/signup" onClick={() => setMobileMenuOpen(false)}>
                  <Button
                    w="full"
                    h={11}
                    rounded="xl"
                    bg="ui.text"
                    color="ui.panel"
                    _hover={{ bg: "ui.panelInverse" }}
                  >
                    Sign Up
                  </Button>
                </Link>
              )}
            </Box>
          </Stack>
        </Box>
      </Container>
    </Box>
  )
}

export default LandingNavbar
