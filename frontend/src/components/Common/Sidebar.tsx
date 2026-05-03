import { Box, Flex, Icon, IconButton, Text } from "@chakra-ui/react"
import { Link as RouterLink, useLocation } from "@tanstack/react-router"
import { useEffect, useMemo, useState } from "react"
import { useTranslation } from "react-i18next"
import { FaBars } from "react-icons/fa"
import {
  FiChevronDown,
  FiChevronRight,
  FiHome,
  FiLogOut,
  FiSearch,
  FiSettings,
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
import ThemeLogo from "./ThemeLogo"

type SidebarRoute =
  | "/overview"
  | "/creators-search"
  | "/brand-intelligence"
  | "/brand-intelligence/reputation-strategy"
  | "/settings"
  | "/admin"

type SidebarChildItem = {
  key: string
  title: string
  path: SidebarRoute
}

type SidebarItem = {
  key: string
  icon: IconType
  title: string
  path?: SidebarRoute
  children?: SidebarChildItem[]
  placeholder?: boolean
  danger?: boolean
}

const topItems: SidebarItem[] = [
  { key: "overview", icon: FiHome, title: "", path: "/overview" },
  {
    key: "creators-search",
    icon: FiSearch,
    title: "Creators Search",
    path: "/creators-search",
  },
  {
    key: "brand-intelligence",
    icon: FiUsers,
    title: "Brand Intelligence",
    children: [
      {
        key: "reputation-strategy",
        title: "Reputation Strategy",
        path: "/brand-intelligence/reputation-strategy",
      },
    ],
  },
]

const isActiveRoute = (pathname: string, route: SidebarRoute) => {
  if (route === "/overview") {
    return pathname === route
  }
  return pathname === route || pathname.startsWith(`${route}/`)
}

type SidebarNavItemProps = {
  item: SidebarItem
  currentPath: string
  isExpanded?: boolean
  onNavigate?: () => void
  onLogout: () => void
  onToggleExpand?: (key: string) => void
}

const SidebarNavItem = ({
  item,
  currentPath,
  isExpanded = false,
  onNavigate,
  onLogout,
  onToggleExpand,
}: SidebarNavItemProps) => {
  const hasChildren = (item.children?.length ?? 0) > 0
  const isChildActive = item.children?.some((child) =>
    isActiveRoute(currentPath, child.path),
  )
  const isActive = item.path
    ? isActiveRoute(currentPath, item.path)
    : Boolean(isChildActive)

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
    color: item.danger
      ? "ui.danger"
      : isActive
        ? "ui.link"
        : "ui.secondaryText",
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
          bg: "ui.link",
        }
      : undefined,
    opacity: item.placeholder ? 0.85 : 1,
    cursor: item.placeholder ? "not-allowed" : "pointer",
  } as const

  const itemContent = (
    <Flex {...baseStyles} justifyContent="space-between">
      <Flex alignItems="center" gap={3} minW={0}>
        <Icon as={item.icon} boxSize={5} />
        <Text
          fontSize="md"
          fontWeight={isActive ? "bold" : "medium"}
          letterSpacing="-0.01em"
          flex="1"
          minW={0}
          whiteSpace="normal"
          lineHeight="1.3"
        >
          {item.title}
        </Text>
      </Flex>

      {hasChildren ? (
        <Icon
          as={isExpanded ? FiChevronDown : FiChevronRight}
          boxSize={4.5}
          flexShrink={0}
        />
      ) : null}
    </Flex>
  )

  if (hasChildren) {
    const sectionId = `sidebar-section-${item.key}`

    return (
      <Box>
        <Box
          as="button"
          w="full"
          textAlign="left"
          onClick={() => onToggleExpand?.(item.key)}
          aria-expanded={isExpanded}
          aria-controls={sectionId}
        >
          {itemContent}
        </Box>

        <Box
          id={sectionId}
          overflow="hidden"
          maxH={isExpanded ? "240px" : "0px"}
          opacity={isExpanded ? 1 : 0}
          transition="max-height 180ms ease, opacity 180ms ease"
          pl={1}
          pr={1}
        >
          <Box ml={3} pl={8} py={1}>
            <Flex direction="column" gap={1}>
              {item.children?.map((child, index) => {
                const isChildRouteActive = isActiveRoute(
                  currentPath,
                  child.path,
                )
                const isFirstChild = index === 0

                return (
                  <Box
                    key={child.key}
                    position="relative"
                    _before={{
                      content: '""',
                      position: "absolute",
                      left: "-22px",
                      top: isFirstChild ? "-12px" : "-8px",
                      width: "22px",
                      height: isFirstChild
                        ? "calc(50% + 12px)"
                        : "calc(50% + 8px)",
                      borderLeftWidth: "1px",
                      borderBottomWidth: "1px",
                      borderColor: "ui.sidebarBorder",
                      borderBottomLeftRadius: "12px",
                    }}
                  >
                    <RouterLink to={child.path} onClick={onNavigate}>
                      <Flex
                        alignItems="center"
                        justifyContent="center"
                        rounded="xl"
                        px={4}
                        py={2.5}
                        minH="11"
                        textAlign="center"
                        transition="all 180ms ease"
                        borderWidth="1px"
                        borderColor={
                          isChildRouteActive
                            ? "ui.sidebarBorder"
                            : "transparent"
                        }
                        bg={
                          isChildRouteActive ? "ui.activeSoft" : "transparent"
                        }
                        color={
                          isChildRouteActive ? "ui.link" : "ui.secondaryText"
                        }
                        _hover={{
                          bg: isChildRouteActive
                            ? "ui.activeSoft"
                            : "ui.surfaceSoft",
                          borderColor: "ui.sidebarBorder",
                        }}
                      >
                        <Text
                          fontSize="xs"
                          fontWeight={isChildRouteActive ? "bold" : "medium"}
                          letterSpacing="-0.01em"
                          whiteSpace="normal"
                          lineHeight="1.3"
                        >
                          {child.title}
                        </Text>
                      </Flex>
                    </RouterLink>
                  </Box>
                )
              })}
            </Flex>
          </Box>
        </Box>
      </Box>
    )
  }

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
  const { t } = useTranslation("common")
  const { t: tCreatorsSearch } = useTranslation("creatorsSearch")
  const { t: tBrandIntelligence } = useTranslation("brandIntelligence")
  const profileSubLabel = isSuperuser
    ? t("labels.adminPlan")
    : userEmail || t("labels.noEmail")
  const localizedTopItems = useMemo(
    () =>
      topItems.map((item) =>
        item.key === "overview"
          ? { ...item, title: t("navigation.overview") }
          : item.key === "creators-search"
            ? {
                ...item,
                title: tCreatorsSearch("shell.navigation.title"),
              }
            : item.key === "brand-intelligence"
              ? {
                  ...item,
                  title: tBrandIntelligence("shell.navigation.title"),
                  children: item.children?.map((child) =>
                    child.key === "reputation-strategy"
                      ? {
                          ...child,
                          title: tBrandIntelligence(
                            "shell.navigation.reputationStrategy",
                          ),
                        }
                      : child,
                  ),
                }
              : item,
      ),
    [t, tBrandIntelligence, tCreatorsSearch],
  )
  const [expandedSections, setExpandedSections] = useState<
    Record<string, boolean>
  >(() =>
    Object.fromEntries(
      localizedTopItems
        .filter((item) =>
          item.children?.some((child) =>
            isActiveRoute(currentPath, child.path),
          ),
        )
        .map((item) => [item.key, true]),
    ),
  )

  const bottomItems: SidebarItem[] = useMemo(
    () => [
      ...(isSuperuser
        ? [
            {
              key: "admin",
              icon: FiUsers,
              title: t("navigation.admin"),
              path: "/admin" as const,
            },
          ]
        : []),
      {
        key: "settings",
        icon: FiSettings,
        title: t("navigation.settings"),
        path: "/settings" as const,
      },
      {
        key: "logout",
        icon: FiLogOut,
        title: t("navigation.logout"),
        danger: true,
      },
    ],
    [isSuperuser, t],
  )

  useEffect(() => {
    setExpandedSections((current) => {
      let hasChanges = false
      const nextState = { ...current }

      for (const item of localizedTopItems) {
        const isChildRouteActive = item.children?.some((child) =>
          isActiveRoute(currentPath, child.path),
        )

        if (isChildRouteActive && !nextState[item.key]) {
          nextState[item.key] = true
          hasChanges = true
        }
      }

      return hasChanges ? nextState : current
    })
  }, [currentPath, localizedTopItems])

  const handleToggleExpand = (key: string) => {
    setExpandedSections((current) => ({
      ...current,
      [key]: !current[key],
    }))
  }

  return (
    <Flex
      direction="column"
      h="full"
      w="full"
      bg="ui.panel"
      borderRightWidth="1px"
      borderRightColor="ui.sidebarBorder"
    >
      <Flex px={6} py={7} alignItems="center" gap={3}>
        <ThemeLogo
          h="14"
          w="auto"
          display="block"
          transform={{ base: "translateY(-5px)", sm: "translateY(-6px)" }}
        />
      </Flex>

      <Flex direction="column" gap={1} px={4} pb={4}>
        {localizedTopItems.map((item) => (
          <SidebarNavItem
            key={item.key}
            item={item}
            currentPath={currentPath}
            isExpanded={Boolean(expandedSections[item.key])}
            onNavigate={onNavigate}
            onLogout={onLogout}
            onToggleExpand={handleToggleExpand}
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
              key={item.key}
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
              bg="ui.brandGlow"
              color="ui.brandText"
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
                {userName?.trim() || t("labels.user")}
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
  const { t } = useTranslation("common")
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
            aria-label={t("menu.open")}
            position="fixed"
            top={3}
            left={3}
            zIndex={100}
            bg="ui.panel"
            borderWidth="1px"
            borderColor="ui.sidebarBorder"
            rounded="xl"
            boxShadow="ui.panelSm"
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
