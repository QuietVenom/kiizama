import {
  Box,
  Button,
  ButtonGroup,
  Flex,
  HStack,
  Icon,
  Text,
} from "@chakra-ui/react"
import { useEffect, useState } from "react"
import { AiFillDelete } from "react-icons/ai"
import { FaDownload } from "react-icons/fa"
import { FiDelete, FiHardDrive } from "react-icons/fi"

import {
  DialogActionTrigger,
  DialogBody,
  DialogContent,
  DialogFooter,
  DialogHeader,
  DialogRoot,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog"
import {
  clearLocalReports,
  deleteLocalReport,
  downloadLocalReport,
  formatLocalReportDate,
  type LocalReportItem,
  MAX_LOCAL_REPORTS,
  readLocalReports,
  subscribeToLocalReports,
} from "@/lib/local-reports"

const deleteButtonStyles = {
  bg: "ui.panelAlt",
  color: "ui.neutralText",
  _hover: {
    bg: "ui.danger",
    color: "ui.textInverse",
  },
} as const

const downloadButtonStyles = {
  bg: "ui.brandSoft",
  color: "ui.brandText",
  _hover: {
    bg: "ui.main",
    color: "ui.panel",
  },
} as const

const RecentReportsCard = () => {
  const [items, setItems] = useState<LocalReportItem[]>(() =>
    readLocalReports(),
  )
  const [isDeleteAllOpen, setIsDeleteAllOpen] = useState(false)
  const [itemToDelete, setItemToDelete] = useState<LocalReportItem | null>(null)
  const shouldEnableListScroll = items.length >= 5

  useEffect(() => {
    return subscribeToLocalReports(setItems)
  }, [])

  const onDeleteAll = () => {
    clearLocalReports()
    setIsDeleteAllOpen(false)
  }

  const onDeleteItem = () => {
    if (!itemToDelete) return

    deleteLocalReport(itemToDelete.id)
    setItemToDelete(null)
  }

  return (
    <Box layerStyle="dashboardCard" p={{ base: 5, lg: 7 }} minW={0}>
      <Flex
        alignItems={{ base: "flex-start", md: "center" }}
        justifyContent="space-between"
        mb={6}
        gap={4}
        direction={{ base: "column", md: "row" }}
      >
        <HStack gap={3} alignItems="flex-start" minW={0}>
          <Flex direction="column" alignItems="center" minW="72px">
            <Icon as={FiHardDrive} color="ui.brandText" boxSize={7} />
            <Text
              mt={1}
              fontSize={{ base: "sm", lg: "md" }}
              color="ui.secondaryText"
              fontWeight="bold"
            >
              {items.length} / {MAX_LOCAL_REPORTS}
            </Text>
          </Flex>
          <Text
            fontSize={{ base: "lg", lg: "2xl" }}
            fontWeight="black"
            letterSpacing="-0.02em"
            minW={0}
          >
            Available Reports - Local Storage
          </Text>
        </HStack>
        <DialogRoot
          size={{ base: "xs", md: "md" }}
          placement="center"
          open={isDeleteAllOpen}
          onOpenChange={({ open }) => setIsDeleteAllOpen(open)}
        >
          <DialogTrigger asChild>
            <Button
              aria-label="Delete all reports"
              variant="solid"
              boxSize="40px"
              minW="40px"
              p={0}
              disabled={items.length === 0}
              {...deleteButtonStyles}
            >
              <Icon as={AiFillDelete} boxSize={4} />
            </Button>
          </DialogTrigger>
          <DialogContent>
            <DialogHeader>
              <DialogTitle>Estas seguro?</DialogTitle>
            </DialogHeader>
            <DialogBody>
              <Text>
                Se eliminaran todos los reportes disponibles en local storage.
              </Text>
            </DialogBody>
            <DialogFooter>
              <ButtonGroup>
                <DialogActionTrigger asChild>
                  <Button variant="outline">No</Button>
                </DialogActionTrigger>
                <Button
                  colorPalette="red"
                  variant="solid"
                  onClick={onDeleteAll}
                >
                  Si
                </Button>
              </ButtonGroup>
            </DialogFooter>
          </DialogContent>
        </DialogRoot>
      </Flex>

      <Text
        fontSize={{ base: "sm", lg: "md" }}
        color="ui.mutedText"
        fontWeight="medium"
        mb={4}
      >
        List of available reports
      </Text>

      <Box
        maxH={shouldEnableListScroll ? { base: "330px", lg: "370px" } : "none"}
        overflowY={shouldEnableListScroll ? "auto" : "visible"}
        pe={shouldEnableListScroll ? 1 : 0}
        css={
          shouldEnableListScroll
            ? {
                "&::-webkit-scrollbar": { width: "8px" },
                "&::-webkit-scrollbar-thumb": {
                  background: "ui.scrollbarThumb",
                  borderRadius: "8px",
                },
                "&::-webkit-scrollbar-track": { background: "transparent" },
              }
            : undefined
        }
      >
        <Flex direction="column" gap={2.5}>
          {items.length === 0 ? (
            <Box
              rounded="2xl"
              px={{ base: 3, lg: 4 }}
              py={{ base: 4, lg: 5 }}
              borderWidth="1px"
              borderColor="ui.sidebarBorder"
              bg="ui.surfaceSoft"
            >
              <Text fontWeight="bold" color="ui.secondaryText">
                No reports available in local storage.
              </Text>
            </Box>
          ) : (
            items.map((item) => (
              <Flex
                key={item.id}
                alignItems={{ base: "stretch", sm: "center" }}
                justifyContent="space-between"
                gap={{ base: 3, lg: 4 }}
                direction={{ base: "column", sm: "row" }}
                rounded="2xl"
                px={{ base: 3, lg: 4 }}
                py={{ base: 2.5, lg: 3 }}
                transition="background-color 180ms ease, border-color 180ms ease"
                borderWidth="1px"
                borderColor="transparent"
                _hover={{
                  bg: "ui.surfaceSoft",
                  borderColor: "ui.sidebarBorder",
                }}
              >
                <HStack gap={4} minW={0} alignItems="flex-start" w="full">
                  <Box minW={0}>
                    <Text
                      fontSize={{ base: "sm", lg: "lg" }}
                      fontWeight="bold"
                      lineHeight="1.1"
                      truncate
                    >
                      {item.name}
                    </Text>
                    <Text
                      fontSize={{ base: "xs", lg: "sm" }}
                      color="ui.mutedText"
                      fontWeight="medium"
                      truncate
                    >
                      Saved on {formatLocalReportDate(item.createdAt)}
                    </Text>
                  </Box>
                </HStack>

                <HStack gap={2} alignSelf={{ base: "flex-end", sm: "initial" }}>
                  <Button
                    aria-label={`Download report ${item.name}`}
                    variant="solid"
                    size="sm"
                    onClick={() => downloadLocalReport(item)}
                    {...downloadButtonStyles}
                  >
                    <Icon as={FaDownload} boxSize={3.5} />
                  </Button>
                  <Button
                    aria-label={`Delete report ${item.name}`}
                    variant="solid"
                    size="sm"
                    onClick={() => setItemToDelete(item)}
                    {...deleteButtonStyles}
                  >
                    <Icon as={FiDelete} boxSize={4} />
                  </Button>
                </HStack>
              </Flex>
            ))
          )}
        </Flex>
      </Box>

      <DialogRoot
        size={{ base: "xs", md: "md" }}
        placement="center"
        open={!!itemToDelete}
        onOpenChange={({ open }) => {
          if (!open) setItemToDelete(null)
        }}
      >
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Estas seguro?</DialogTitle>
          </DialogHeader>
          <DialogBody>
            <Text>
              Se eliminara el reporte{" "}
              <Text as="span" fontWeight="bold">
                {itemToDelete?.name}
              </Text>
              .
            </Text>
          </DialogBody>
          <DialogFooter>
            <ButtonGroup>
              <DialogActionTrigger asChild>
                <Button variant="outline">No</Button>
              </DialogActionTrigger>
              <Button colorPalette="red" variant="solid" onClick={onDeleteItem}>
                Si
              </Button>
            </ButtonGroup>
          </DialogFooter>
        </DialogContent>
      </DialogRoot>
    </Box>
  )
}

export default RecentReportsCard
