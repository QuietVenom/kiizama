import {
  Badge,
  Box,
  Button,
  Flex,
  Icon,
  IconButton,
  Text,
} from "@chakra-ui/react"
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import { FiBell, FiCalendar } from "react-icons/fi"

import {
  billingNoticesQueryKey,
  billingSummaryQueryKey,
  dismissBillingNotice,
  markBillingNoticeRead,
  readBillingNotices,
} from "@/features/billing/api"
import { MenuContent, MenuRoot, MenuTrigger } from "../ui/menu"

const formatToday = () =>
  new Intl.DateTimeFormat("es-MX", {
    day: "2-digit",
    month: "long",
    year: "numeric",
    timeZone: "America/Mexico_City",
  }).format(new Date())

const DashboardTopbar = () => {
  const queryClient = useQueryClient()
  const { data } = useQuery({
    queryKey: billingNoticesQueryKey,
    queryFn: readBillingNotices,
    staleTime: 30_000,
  })

  const notices = data?.data ?? []
  const unreadCount = notices.filter(
    (notice) => notice.status === "unread",
  ).length

  const invalidateBillingQueries = () => {
    void queryClient.invalidateQueries({ queryKey: billingNoticesQueryKey })
    void queryClient.invalidateQueries({ queryKey: billingSummaryQueryKey })
  }

  const readMutation = useMutation({
    mutationFn: markBillingNoticeRead,
    onSuccess: invalidateBillingQueries,
  })

  const dismissMutation = useMutation({
    mutationFn: dismissBillingNotice,
    onSuccess: invalidateBillingQueries,
  })

  return (
    <Flex
      as="header"
      alignItems="center"
      justifyContent="flex-end"
      gap={4}
      borderBottomWidth="1px"
      borderBottomColor="ui.sidebarBorder"
      bg="ui.panel"
      ps={{ base: 16, md: 0 }}
      pe={{ base: 4, md: 7, lg: 10 }}
      py={3}
      position="sticky"
      top={0}
      zIndex={5}
    >
      <Flex alignItems="center" gap={3}>
        <MenuRoot>
          <MenuTrigger asChild>
            <Box position="relative">
              <IconButton
                aria-label="Billing notices"
                variant="outline"
                rounded="2xl"
              >
                <FiBell />
              </IconButton>
              {unreadCount > 0 ? (
                <Badge
                  position="absolute"
                  top="-1"
                  right="-1"
                  rounded="full"
                  colorPalette="red"
                  minW="5"
                  textAlign="center"
                >
                  {unreadCount}
                </Badge>
              ) : null}
            </Box>
          </MenuTrigger>
          <MenuContent minW="24rem" p={2}>
            {notices.length === 0 ? (
              <Box px={3} py={4}>
                <Text fontWeight="bold">No billing notices</Text>
                <Text mt={1} color="ui.secondaryText" fontSize="sm">
                  Upcoming renewals and trial reminders will appear here.
                </Text>
              </Box>
            ) : (
              notices.map((notice) => (
                <Box
                  key={notice.id}
                  px={3}
                  py={3}
                  borderBottomWidth="1px"
                  borderBottomColor="ui.border"
                >
                  <Flex align="center" justify="space-between" gap={3}>
                    <Text fontWeight="bold">{notice.title}</Text>
                    <Badge
                      colorPalette={notice.status === "unread" ? "red" : "gray"}
                    >
                      {notice.status}
                    </Badge>
                  </Flex>
                  <Text mt={2} fontSize="sm" color="ui.secondaryText">
                    {notice.message}
                  </Text>
                  <Flex mt={3} gap={2}>
                    {notice.status === "unread" ? (
                      <Button
                        size="xs"
                        variant="outline"
                        loading={readMutation.isPending}
                        onClick={() => readMutation.mutate(notice.id)}
                      >
                        Mark as read
                      </Button>
                    ) : null}
                    <Button
                      size="xs"
                      variant="ghost"
                      loading={dismissMutation.isPending}
                      onClick={() => dismissMutation.mutate(notice.id)}
                    >
                      Dismiss
                    </Button>
                  </Flex>
                </Box>
              ))
            )}
          </MenuContent>
        </MenuRoot>
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
