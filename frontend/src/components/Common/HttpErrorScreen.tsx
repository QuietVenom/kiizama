import { Box, Button, Center, Flex, HStack, Text } from "@chakra-ui/react"
import { Link } from "@tanstack/react-router"

type HttpErrorScreenProps = {
  dataTestId: string
  message: string
  primaryActionHref?: string
  primaryActionLabel?: string
  onPrimaryAction?: () => void
  secondaryActionHref?: string
  secondaryActionLabel?: string
  statusCode: 403 | 404 | 500 | 503
  title: string
}

const HttpErrorScreen = ({
  dataTestId,
  message,
  onPrimaryAction,
  primaryActionHref,
  primaryActionLabel,
  secondaryActionHref,
  secondaryActionLabel,
  statusCode,
  title,
}: HttpErrorScreenProps) => {
  const primaryActionButton = onPrimaryAction ? (
    <Button
      variant="solid"
      colorPalette="design"
      mt={4}
      alignSelf="center"
      onClick={onPrimaryAction}
    >
      {primaryActionLabel}
    </Button>
  ) : primaryActionHref ? (
    <Link to={primaryActionHref}>
      <Button variant="solid" colorPalette="design" mt={4} alignSelf="center">
        {primaryActionLabel}
      </Button>
    </Link>
  ) : null

  return (
    <Flex
      height="100vh"
      align="center"
      justify="center"
      flexDir="column"
      data-testid={dataTestId}
      p={4}
      bg="ui.page"
    >
      <Flex alignItems="center" zIndex={1}>
        <Flex flexDir="column" ml={4} align="center" justify="center" p={4}>
          <Text
            fontSize={{ base: "6xl", md: "8xl" }}
            fontWeight="bold"
            lineHeight="1"
            mb={4}
          >
            {statusCode}
          </Text>
          <Text fontSize="2xl" fontWeight="bold" mb={2}>
            {title}
          </Text>
        </Flex>
      </Flex>

      <Text
        fontSize="lg"
        color="ui.secondaryText"
        mb={4}
        textAlign="center"
        zIndex={1}
        maxW="xl"
      >
        {message}
      </Text>
      <Center zIndex={1}>
        <HStack gap={3} wrap="wrap" justify="center">
          {primaryActionButton}
          {secondaryActionHref && secondaryActionLabel ? (
            <Link to={secondaryActionHref}>
              <Button variant="outline" mt={4} alignSelf="center">
                {secondaryActionLabel}
              </Button>
            </Link>
          ) : null}
        </HStack>
      </Center>
      <Box
        position="absolute"
        top="-20"
        right="-20"
        w={{ base: "60", md: "88" }}
        h={{ base: "60", md: "88" }}
        layerStyle="publicGlowPrimary"
        opacity={0.65}
      />
      <Box
        position="absolute"
        top="18%"
        left="-16"
        w={{ base: "52", md: "72" }}
        h={{ base: "52", md: "72" }}
        layerStyle="publicGlowSecondary"
        opacity={0.7}
      />
    </Flex>
  )
}

export default HttpErrorScreen
