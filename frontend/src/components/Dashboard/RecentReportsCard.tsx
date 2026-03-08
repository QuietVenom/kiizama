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

type LocalReportItem = {
  id: string
  name: string
  createdAt: string
}

const defaultItems: LocalReportItem[] = [
  {
    id: "report-1",
    name: "profile_mining_q1_2026.json",
    createdAt: "02 Apr 2026",
  },
  {
    id: "report-2",
    name: "creator_report_fashion_team.pdf",
    createdAt: "01 Apr 2026",
  },
  {
    id: "report-3",
    name: "reputation_campaign_strategy_v2.pdf",
    createdAt: "30 Mar 2026",
  },
  {
    id: "report-4",
    name: "reputation_creator_strategy_batch_03.pdf",
    createdAt: "28 Mar 2026",
  },
  {
    id: "report-5",
    name: "5reputation_creator_strategy_batch_03.pdf",
    createdAt: "28 Mar 2026",
  },
  {
    id: "report-6",
    name: "6reputation_creator_strategy_batch_03.pdf",
    createdAt: "28 Mar 2026",
  },
  {
    id: "report-7",
    name: "7reputation_creator_strategy_batch_03.pdf",
    createdAt: "28 Mar 2026",
  },
  {
    id: "report-8",
    name: "8reputation_creator_strategy_batch_03.pdf",
    createdAt: "28 Mar 2026",
  },
  {
    id: "report-9",
    name: "9reputation_creator_strategy_batch_03.pdf",
    createdAt: "28 Mar 2026",
  },
]

const STORAGE_KEY = "kiizama-overview-local-reports"

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

const isLocalReportItem = (value: unknown): value is LocalReportItem => {
  if (!value || typeof value !== "object") return false
  const report = value as Record<string, unknown>
  return (
    typeof report.id === "string" &&
    typeof report.name === "string" &&
    typeof report.createdAt === "string"
  )
}

const readStoredReports = (): LocalReportItem[] => {
  if (typeof window === "undefined") return defaultItems

  try {
    const rawValue = localStorage.getItem(STORAGE_KEY)
    if (!rawValue) return defaultItems

    const parsedValue: unknown = JSON.parse(rawValue)
    if (!Array.isArray(parsedValue)) return defaultItems
    if (parsedValue.length === 0) return []

    const reports = parsedValue.filter(isLocalReportItem)
    return reports.length > 0 ? reports : defaultItems
  } catch {
    return defaultItems
  }
}

const buildDownloadFile = (item: LocalReportItem) => {
  const reportSummary = {
    id: item.id,
    name: item.name,
    createdAt: item.createdAt,
    source: "Kiizama local storage",
  }
  const isJsonReport = item.name.toLowerCase().endsWith(".json")

  if (isJsonReport) {
    return {
      blob: new Blob([JSON.stringify(reportSummary, null, 2)], {
        type: "application/json;charset=utf-8",
      }),
      filename: item.name,
    }
  }

  const baseName = item.name.replace(/\.[^.]+$/, "")
  const textContent = [
    "Kiizama Local Report",
    `Report: ${item.name}`,
    `Saved on: ${item.createdAt}`,
    "",
    "This download contains the local report reference currently available in the dashboard.",
  ].join("\n")

  return {
    blob: new Blob([textContent], { type: "text/plain;charset=utf-8" }),
    filename: `${baseName}.txt`,
  }
}

const RecentReportsCard = () => {
  const [items, setItems] = useState<LocalReportItem[]>(() =>
    readStoredReports(),
  )
  const [isDeleteAllOpen, setIsDeleteAllOpen] = useState(false)
  const [itemToDelete, setItemToDelete] = useState<LocalReportItem | null>(null)
  const shouldEnableListScroll = items.length >= 5

  useEffect(() => {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(items))
  }, [items])

  const onDeleteAll = () => {
    setItems([])
    setIsDeleteAllOpen(false)
  }

  const onDeleteItem = () => {
    if (!itemToDelete) return
    setItems((prevItems) =>
      prevItems.filter((item) => item.id !== itemToDelete.id),
    )
    setItemToDelete(null)
  }

  const onDownloadItem = (item: LocalReportItem) => {
    const { blob, filename } = buildDownloadFile(item)
    const objectUrl = window.URL.createObjectURL(blob)
    const link = document.createElement("a")

    link.href = objectUrl
    link.download = filename
    document.body.appendChild(link)
    link.click()
    document.body.removeChild(link)
    window.URL.revokeObjectURL(objectUrl)
  }

  return (
    <Box layerStyle="dashboardCard" p={{ base: 5, lg: 7 }}>
      <Flex
        alignItems={{ base: "flex-start", md: "center" }}
        justifyContent="space-between"
        mb={6}
        gap={4}
        direction={{ base: "column", md: "row" }}
      >
        <HStack gap={3} alignItems="flex-start">
          <Flex direction="column" alignItems="center" minW="72px">
            <Icon as={FiHardDrive} color="ui.brandText" boxSize={7} />
            <Text
              mt={1}
              fontSize={{ base: "sm", lg: "md" }}
              color="ui.secondaryText"
              fontWeight="bold"
            >
              10 / 10
            </Text>
          </Flex>
          <Text
            fontSize={{ base: "lg", lg: "2xl" }}
            fontWeight="black"
            letterSpacing="-0.02em"
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
                alignItems="center"
                justifyContent="space-between"
                gap={{ base: 3, lg: 4 }}
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
                <HStack gap={4} minW={0} alignItems="flex-start">
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
                      Saved on {item.createdAt}
                    </Text>
                  </Box>
                </HStack>

                <HStack gap={2}>
                  <Button
                    aria-label={`Download report ${item.name}`}
                    variant="solid"
                    size="sm"
                    onClick={() => onDownloadItem(item)}
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
