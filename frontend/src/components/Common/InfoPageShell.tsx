import { Box, Container, IconButton, Image, Stack } from "@chakra-ui/react"
import { Link as RouterLink } from "@tanstack/react-router"
import type { ReactNode } from "react"
import SymbolLogo from "/assets/images/symbol.svg"

type InfoPageShellProps = {
  children: ReactNode
  maxW?: string
  useSymbolHomeButton?: boolean
}

const InfoPageShell = ({
  children,
  maxW = "4xl",
  useSymbolHomeButton = false,
}: InfoPageShellProps) => {
  return (
    <Box
      minH="100vh"
      position="relative"
      overflow="hidden"
      layerStyle="publicPage"
      py={{ base: 12, md: 16 }}
    >
      <Box
        position="absolute"
        top="-24"
        right="-20"
        w={{ base: "64", md: "88" }}
        h={{ base: "64", md: "88" }}
        layerStyle="publicGlowPrimary"
      />
      <Box
        position="absolute"
        top="20%"
        left="-20"
        w={{ base: "52", md: "68" }}
        h={{ base: "52", md: "68" }}
        layerStyle="publicGlowSecondary"
      />

      <Container maxW={maxW} position="relative">
        <Stack gap={6}>
          <Box position="fixed" top="1rem" right="1rem" zIndex={20}>
            <RouterLink to="/">
              <IconButton
                aria-label="Go to landing page"
                bg="ui.panel"
                color="ui.brandText"
                borderWidth="1px"
                borderColor="ui.brandBorderSoft"
                rounded="full"
                boxShadow="ui.panelSm"
                _hover={{ bg: "ui.brandSoft" }}
              >
                {useSymbolHomeButton ? (
                  <Image src={SymbolLogo} alt="Kiizama symbol" boxSize="5" />
                ) : (
                  "K"
                )}
              </IconButton>
            </RouterLink>
          </Box>

          {children}
        </Stack>
      </Container>
    </Box>
  )
}

export default InfoPageShell
