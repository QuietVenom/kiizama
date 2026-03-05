import {
  Box,
  Link as ChakraLink,
  Container,
  HStack,
  IconButton,
  Image,
  Stack,
} from "@chakra-ui/react"
import { Link } from "@tanstack/react-router"
import type { RefObject } from "react"
import { useState } from "react"
import { FiMenu, FiX } from "react-icons/fi"
import { Button } from "@/components/ui/button"
import { getAppUrl } from "@/utils"

type SectionKey = "home" | "features" | "pricing" | "faq"

const sectionLinks: { key: SectionKey; label: string }[] = [
  { key: "home", label: "Home" },
  { key: "features", label: "Capabilities" },
  { key: "pricing", label: "Plans" },
  { key: "faq", label: "FAQ" },
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

type LandingNavbarProps = {
  isWaitingListEnabled: boolean
  navbarRef: RefObject<HTMLElement | null>
  sectionRefs: Record<SectionKey, RefObject<HTMLElement | null>>
}

const LandingNavbar = ({
  isWaitingListEnabled,
  navbarRef,
  sectionRefs,
}: LandingNavbarProps) => {
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false)
  const loginUrl = getAppUrl("/login")

  const handleSectionClick = (key: SectionKey) => {
    if (mobileMenuOpen) {
      setMobileMenuOpen(false)
      window.setTimeout(() => {
        scrollToSection(sectionRefs[key], navbarRef)
      }, MOBILE_MENU_ANIMATION_MS)
      return
    }
    scrollToSection(sectionRefs[key], navbarRef)
  }

  return (
    <Box
      ref={navbarRef}
      as="header"
      position="sticky"
      top={0}
      zIndex="docked"
      bg="rgba(255, 255, 255, 0.84)"
      borderBottomWidth="1px"
      borderBottomColor="orange.100"
      backdropFilter="blur(12px)"
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
              <Image
                src="/assets/images/noBgColor.svg"
                alt="Kiizama logo"
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
            {sectionLinks.map((link) => (
              <Button
                key={link.key}
                variant="ghost"
                color={link.key === "home" ? "gray.900" : "gray.600"}
                fontWeight={link.key === "home" ? "semibold" : "medium"}
                fontSize="sm"
                px={3}
                h={10}
                _hover={{ color: "orange.500", bg: "transparent" }}
                onClick={() =>
                  scrollToSection(sectionRefs[link.key], navbarRef)
                }
              >
                {link.label}
              </Button>
            ))}
          </HStack>

          <HStack
            gap={2}
            justifySelf={{ base: "auto", md: "end" }}
            display={{ base: "none", md: "flex" }}
          >
            <ChakraLink href={loginUrl} _hover={{ textDecoration: "none" }}>
              <Button
                variant="ghost"
                color="gray.600"
                fontWeight="semibold"
                _hover={{ bg: "transparent", color: "gray.900" }}
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
                  bg="gray.900"
                  color="white"
                  _hover={{ bg: "gray.800" }}
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
                  bg="gray.900"
                  color="white"
                  _hover={{ bg: "gray.800" }}
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
            color="gray.800"
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
          borderColor="orange.100"
          rounded="2xl"
          bg="white"
          boxShadow={mobileMenuOpen ? "lg" : "none"}
          overflow="hidden"
          maxH={mobileMenuOpen ? "420px" : "0px"}
          opacity={mobileMenuOpen ? 1 : 0}
          transform={mobileMenuOpen ? "translateY(0)" : "translateY(-8px)"}
          transition="max-height 280ms ease, opacity 220ms ease, transform 280ms ease, margin 280ms ease"
          pointerEvents={mobileMenuOpen ? "auto" : "none"}
        >
          <Stack gap={0}>
            {sectionLinks.map((link) => (
              <Button
                key={link.key}
                variant="ghost"
                justifyContent="flex-start"
                borderRadius={0}
                h="12"
                borderBottomWidth="1px"
                borderBottomColor="orange.100"
                color={link.key === "home" ? "gray.900" : "gray.600"}
                fontWeight={link.key === "home" ? "semibold" : "medium"}
                onClick={() => handleSectionClick(link.key)}
              >
                {link.label}
              </Button>
            ))}
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
                color="gray.600"
                borderBottomWidth="1px"
                borderBottomColor="orange.100"
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
                    bg="gray.900"
                    color="white"
                    _hover={{ bg: "gray.800" }}
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
                    bg="gray.900"
                    color="white"
                    _hover={{ bg: "gray.800" }}
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
