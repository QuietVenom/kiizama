import { Box, Container, IconButton, Stack } from "@chakra-ui/react"
import { Link as RouterLink } from "@tanstack/react-router"
import type { ReactNode } from "react"

type InfoPageShellProps = {
  children: ReactNode
  maxW?: string
}

const InfoPageShell = ({ children, maxW = "4xl" }: InfoPageShellProps) => {
  return (
    <Box
      minH="100vh"
      position="relative"
      overflow="hidden"
      bgGradient="linear(to-b, #FFFDF8, #FFF9ED 48%, white)"
      py={{ base: 12, md: 16 }}
    >
      <Box
        position="absolute"
        top="-24"
        right="-20"
        w={{ base: "64", md: "88" }}
        h={{ base: "64", md: "88" }}
        rounded="full"
        bg="orange.100"
        opacity={0.5}
        filter="blur(100px)"
      />
      <Box
        position="absolute"
        top="20%"
        left="-20"
        w={{ base: "52", md: "68" }}
        h={{ base: "52", md: "68" }}
        rounded="full"
        bg="orange.50"
        opacity={0.8}
        filter="blur(90px)"
      />

      <Container maxW={maxW} position="relative">
        <Stack gap={6}>
          <RouterLink
            to="/"
            style={{
              position: "fixed",
              top: "1rem",
              right: "1rem",
              zIndex: 20,
            }}
          >
            <IconButton
              aria-label="Go to landing page"
              bg="white"
              color="orange.500"
              borderWidth="1px"
              borderColor="orange.100"
              rounded="full"
              boxShadow="sm"
              _hover={{ bg: "orange.50" }}
            >
              K
            </IconButton>
          </RouterLink>

          {children}
        </Stack>
      </Container>
    </Box>
  )
}

export default InfoPageShell
