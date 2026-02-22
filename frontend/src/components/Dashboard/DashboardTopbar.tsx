import { Box, Flex, Icon, IconButton, Input, Text } from "@chakra-ui/react"
import { FiBell, FiCalendar, FiSearch } from "react-icons/fi"

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
      justifyContent="space-between"
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
      <Box
        position="relative"
        flex={1}
        maxW={{ base: "full", lg: "560px" }}
        ms={{ base: 0, md: 4, lg: 6 }}
      >
        <Icon
          as={FiSearch}
          color="ui.secondaryText"
          boxSize={4}
          position="absolute"
          left={3.5}
          top="50%"
          transform="translateY(-50%)"
          zIndex={1}
          pointerEvents="none"
        />
        <Input
          placeholder="Search creators, reports..."
          bg="ui.surfaceSoft"
          borderWidth="1px"
          borderColor="ui.sidebarBorder"
          rounded="full"
          h="50px"
          ps={11}
          pe={5}
          fontSize={{ base: "sm", lg: "md" }}
          fontWeight="medium"
          color="ui.secondaryText"
          _placeholder={{ color: "ui.mutedText" }}
          _focusVisible={{
            borderColor: "orange.300",
            boxShadow: "0 0 0 3px rgba(251, 146, 60, 0.14)",
            bg: "white",
          }}
        />
      </Box>

      <Flex alignItems="center" display={{ base: "none", md: "flex" }} gap={3}>
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
          <Box textAlign="right">
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
