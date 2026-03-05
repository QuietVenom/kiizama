import { Box, Flex, Icon, IconButton, Text } from "@chakra-ui/react"
import { FiBell, FiCalendar } from "react-icons/fi"

const formatToday = () =>
  new Intl.DateTimeFormat("es-MX", {
    day: "2-digit",
    month: "long",
    year: "numeric",
    timeZone: "America/Mexico_City",
  }).format(new Date())

const DashboardTopbar = () => {
  return (
    <Flex
      as="header"
      alignItems="center"
      justifyContent="flex-end"
      gap={4}
      borderBottomWidth="1px"
      borderBottomColor="ui.sidebarBorder"
      bg="white"
      ps={{ base: 16, md: 0 }}
      pe={{ base: 4, md: 7, lg: 10 }}
      py={3}
      position="sticky"
      top={0}
      zIndex={5}
    >
      <Flex alignItems="center" gap={3}>
        <IconButton
          aria-label="Notifications"
          variant="ghost"
          position="relative"
          boxSize="40px"
          rounded="xl"
          color="ui.secondaryText"
          borderWidth="1px"
          borderColor="transparent"
          _hover={{
            bg: "ui.surfaceSoft",
            borderColor: "ui.sidebarBorder",
            boxShadow: "sm",
          }}
        >
          <FiBell />
          <Box
            position="absolute"
            top="10px"
            right="10px"
            boxSize="7px"
            rounded="full"
            bg="orange.400"
          />
        </IconButton>

        <Box h={8} w="1px" bg="ui.sidebarBorder" />

        <Flex alignItems="center" gap={3}>
          <Box textAlign="right" display={{ base: "none", sm: "block" }}>
            <Text
              fontSize="xs"
              color="ui.mutedText"
              fontWeight="bold"
              letterSpacing="0.2em"
              textTransform="uppercase"
            >
              Today
            </Text>
            <Text fontSize={{ base: "sm", lg: "md" }} fontWeight="bold">
              {formatToday()}
            </Text>
          </Box>
          <Box
            boxSize="48px"
            rounded="2xl"
            borderWidth="1px"
            borderColor="ui.sidebarBorder"
            bg="ui.surfaceSoft"
            display="inline-flex"
            alignItems="center"
            justifyContent="center"
            color="ui.secondaryText"
          >
            <Icon as={FiCalendar} boxSize={5} />
          </Box>
        </Flex>
      </Flex>
    </Flex>
  )
}

export default DashboardTopbar
