import { Box, Flex, Icon, IconButton, Text } from "@chakra-ui/react"
import { Link as RouterLink, useLocation } from "@tanstack/react-router"
import { useMemo, useState } from "react"
import { FaBars } from "react-icons/fa"
import {
  FiBarChart2,
  FiFileText,
  FiHome,
  FiLogOut,
  FiSettings,
  FiShield,
  FiUsers,
} from "react-icons/fi"
import type { IconType } from "react-icons/lib"

import useAuth from "@/hooks/useAuth"
import {
  DrawerBackdrop,
  DrawerBody,
  DrawerCloseTrigger,
  DrawerContent,
  DrawerRoot,
  DrawerTrigger,
} from "../ui/drawer"

type SidebarRoute = "/app" | "/settings" | "/admin"

type SidebarItem = {
  icon: IconType
  title: string
  path?: SidebarRoute
  placeholder?: boolean
  danger?: boolean
}

const topItems: SidebarItem[] = [
  { icon: FiHome, title: "Overview", path: "/app" },
  { icon: FiBarChart2, title: "Analytics", placeholder: true },
  { icon: FiUsers, title: "Creators", placeholder: true },
  { icon: FiFileText, title: "Reports", placeholder: true },
  { icon: FiShield, title: "Reputation", placeholder: true },
]

const isActiveRoute = (pathname: string, route: SidebarRoute) => {
  if (route === "/app") {
    return pathname === route
  }
  return pathname === route || pathname.startsWith(`${route}/`)
}

type SidebarNavItemProps = {
  item: SidebarItem
  currentPath: string
  onNavigate?: () => void
  onLogout: () => void
}

const SidebarNavItem = ({
  item,
  currentPath,
  onNavigate,
  onLogout,
}: SidebarNavItemProps) => {
  const isActive = item.path ? isActiveRoute(currentPath, item.path) : false

  const baseStyles = {
    alignItems: "center",
    gap: 3,
    rounded: "2xl",
    px: 4,
    py: 3.5,
    w: "full",
    transition: "all 180ms ease",
    borderWidth: "1px",
    borderColor: "transparent",
    position: "relative",
    bg: isActive ? "ui.activeSoft" : "transparent",
    color: item.danger ? "#EF4444" : isActive ? "#F97316" : "ui.secondaryText",
    _hover: item.placeholder
      ? undefined
      : {
          bg: isActive ? "ui.activeSoft" : "ui.surfaceSoft",
          borderColor: "ui.sidebarBorder",
        },
    _before: isActive
      ? {
          content: '""',
          position: "absolute",
          left: 0,
          top: "50%",
          transform: "translateY(-50%)",
          h: "26px",
          w: "4px",
          roundedRight: "full",
          bg: "#F97316",
        }
      : undefined,
    opacity: item.placeholder ? 0.85 : 1,
    cursor: item.placeholder ? "not-allowed" : "pointer",
  } as const

  const itemContent = (
    <Flex {...baseStyles}>
      <Icon as={item.icon} boxSize={5} />
      <Text
        fontSize="md"
        fontWeight={isActive ? "bold" : "medium"}
        letterSpacing="-0.01em"
      >
        {item.title}
      </Text>
    </Flex>
  )

  if (item.path) {
    return (
      <RouterLink to={item.path} onClick={onNavigate}>
        {itemContent}
      </RouterLink>
    )
  }

  if (item.danger) {
    return (
      <Box as="button" onClick={onLogout} textAlign="left">
        {itemContent}
      </Box>
    )
  }

  return (
    <Box
      as="button"
      onClick={undefined}
      textAlign="left"
      aria-disabled
      tabIndex={-1}
      title={`${item.title} coming soon`}
    >
      {itemContent}
    </Box>
  )
}

type SidebarBodyProps = {
  currentPath: string
  isSuperuser: boolean
  onLogout: () => void
  onNavigate?: () => void
  userEmail?: string | null
  userName?: string | null
}

const getInitials = (name?: string | null, email?: string | null) => {
  if (name?.trim()) {
    const parts = name.trim().split(" ").filter(Boolean)
    const initials = parts
      .slice(0, 2)
      .map((part) => part[0]?.toUpperCase())
      .join("")
    if (initials) {
      return initials
    }
  }
  return email?.[0]?.toUpperCase() || "U"
}

const SidebarBody = ({
  currentPath,
  isSuperuser,
  onLogout,
  onNavigate,
  userName,
  userEmail,
}: SidebarBodyProps) => {
  const profileSubLabel = isSuperuser ? "Admin Plan" : userEmail || "No email"

  const bottomItems: SidebarItem[] = useMemo(
    () => [
      ...(isSuperuser
        ? [{ icon: FiUsers, title: "Admin", path: "/admin" as const }]
        : []),
      { icon: FiSettings, title: "Settings", path: "/settings" as const },
      { icon: FiLogOut, title: "Log Out", danger: true },
    ],
    [isSuperuser],
  )

  return (
    <Flex
      direction="column"
      h="full"
      w="full"
      bg="white"
      borderRightWidth="1px"
      borderRightColor="ui.sidebarBorder"
    >
      <Flex px={6} py={7} alignItems="center" gap={3}>
        <Box
          boxSize="60px"
          rounded="2xl"
          bg="linear-gradient(135deg, #FB923C, #F59E0B)"
          color="white"
          boxShadow="0 14px 28px rgba(245, 158, 11, 0.24)"
          display="inline-flex"
          alignItems="center"
          justifyContent="center"
          fontSize="3xl"
          fontWeight="bold"
          fontFamily="'Merriweather', 'Times New Roman', serif"
        >
          K
        </Box>
        <Text fontSize="2xl" fontWeight="black" letterSpacing="-0.02em">
          Kiizama
        </Text>
      </Flex>

      <Flex direction="column" gap={1} px={4} pb={4}>
        {topItems.map((item) => (
          <SidebarNavItem
            key={item.title}
            item={item}
            currentPath={currentPath}
            onNavigate={onNavigate}
            onLogout={onLogout}
          />
        ))}
      </Flex>

      <Flex flex={1} />

      <Box
        px={4}
        pt={3}
        pb={5}
        borderTopWidth="1px"
        borderTopColor="ui.sidebarBorder"
      >
        <Flex direction="column" gap={1}>
          {bottomItems.map((item) => (
            <SidebarNavItem
              key={item.title}
              item={item}
              currentPath={currentPath}
              onNavigate={onNavigate}
              onLogout={onLogout}
            />
          ))}
        </Flex>
      </Box>

      <Box px={5} py={5} borderTopWidth="1px" borderTopColor="ui.sidebarBorder">
        <RouterLink to="/settings" onClick={onNavigate}>
          <Flex alignItems="center" gap={3} rounded="xl" p={2}>
            <Flex
              boxSize="12"
              rounded="full"
              bg="#FDECD7"
              color="#D97706"
              fontSize="xl"
              fontWeight="bold"
              alignItems="center"
              justifyContent="center"
              flexShrink={0}
            >
              {getInitials(userName, userEmail)}
            </Flex>
            <Box minW={0}>
              <Text
                fontSize="md"
                fontWeight="bold"
                letterSpacing="-0.01em"
                lineHeight="1.2"
                truncate
              >
                {userName?.trim() || "User"}
              </Text>
              <Text
                fontSize="xs"
                color="ui.mutedText"
                textTransform={isSuperuser ? "uppercase" : "none"}
                letterSpacing={isSuperuser ? "0.14em" : "normal"}
                fontWeight="semibold"
                truncate
              >
                {profileSubLabel}
              </Text>
            </Box>
          </Flex>
        </RouterLink>
      </Box>
    </Flex>
  )
}

const Sidebar = () => {
  const { pathname } = useLocation()
  const { logout, user } = useAuth()
  const [open, setOpen] = useState(false)

  const handleLogout = () => {
    logout()
    setOpen(false)
  }

  return (
    <>
      <DrawerRoot
        placement="start"
        open={open}
        onOpenChange={(e) => setOpen(e.open)}
      >
        <DrawerBackdrop />
        <DrawerTrigger asChild>
          <IconButton
            variant="ghost"
            color="inherit"
            display={{ base: "flex", md: "none" }}
            aria-label="Open menu"
            position="fixed"
            top={3}
            left={3}
            zIndex={100}
            bg="white"
            borderWidth="1px"
            borderColor="ui.sidebarBorder"
            rounded="xl"
            boxShadow="sm"
          >
            <FaBars />
          </IconButton>
        </DrawerTrigger>
        <DrawerContent maxW="xs" p={0}>
          <DrawerCloseTrigger />
          <DrawerBody p={0}>
            <SidebarBody
              currentPath={pathname}
              isSuperuser={Boolean(user?.is_superuser)}
              onLogout={handleLogout}
              onNavigate={() => setOpen(false)}
              userName={user?.full_name}
              userEmail={user?.email}
            />
          </DrawerBody>
        </DrawerContent>
      </DrawerRoot>

      <Box
        display={{ base: "none", md: "flex" }}
        position="sticky"
        top={0}
        w={{ md: "clamp(245px, 20vw, 270px)" }}
        minW={{ md: "clamp(245px, 20vw, 270px)" }}
        h="100vh"
      >
        <SidebarBody
          currentPath={pathname}
          isSuperuser={Boolean(user?.is_superuser)}
          onLogout={handleLogout}
          userName={user?.full_name}
          userEmail={user?.email}
        />
      </Box>
    </>
  )
}

export default Sidebar
