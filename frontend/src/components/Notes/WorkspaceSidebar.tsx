import { Box, Flex, Text } from "@chakra-ui/react"
import { useEffect, useState } from "react"
import { useTranslation } from "react-i18next"
import { FiPlus, FiTrash2 } from "react-icons/fi"

import { Button } from "@/components/ui/button"
import { formatDate } from "@/i18n"
import type { KanbanBoard } from "@/lib/kanban-store"
import type { Note } from "@/lib/notes-store"

import type { WorkspaceSelection } from "./NotesWorkspaceDialog"

type WorkspaceItemKind = "note" | "board"

const SidebarItem = ({
  isConfirmingDelete,
  isSelected,
  meta,
  onDelete,
  onSelect,
  title,
}: {
  isConfirmingDelete: boolean
  isSelected: boolean
  meta: string
  onDelete: () => void
  onSelect: () => void
  title: string
}) => {
  const { t } = useTranslation("notes")

  return (
    <Flex
      align="center"
      gap={2}
      rounded="18px"
      borderWidth="1px"
      borderColor={isSelected ? "ui.brandBorderSoft" : "transparent"}
      bg={isSelected ? "ui.brandSoft" : "transparent"}
      _hover={{ bg: isSelected ? "ui.brandSoft" : "ui.surfaceSoft" }}
      px={3}
      py={2.5}
    >
      <Box
        as="button"
        flex="1"
        minW={0}
        textAlign="left"
        cursor="pointer"
        onClick={onSelect}
      >
        <Text fontSize="sm" fontWeight="bold" lineClamp={1}>
          {title}
        </Text>
        <Text mt={0.5} color="ui.mutedText" fontSize="xs" lineClamp={1}>
          {meta}
        </Text>
      </Box>

      <Button
        size="2xs"
        variant={isConfirmingDelete ? "solid" : "ghost"}
        colorPalette={isConfirmingDelete ? "red" : undefined}
        color={isConfirmingDelete ? undefined : "ui.mutedText"}
        flexShrink={0}
        aria-label={isConfirmingDelete ? undefined : t("sidebar.delete")}
        onClick={onDelete}
      >
        {isConfirmingDelete ? t("sidebar.confirmDelete") : <FiTrash2 />}
      </Button>
    </Flex>
  )
}

const SectionHeader = ({
  actionLabel,
  onCreate,
  title,
}: {
  actionLabel: string
  onCreate: () => void
  title: string
}) => (
  <Flex align="center" justify="space-between" gap={2} px={1}>
    <Text color="ui.mutedText" fontSize="xs" fontWeight="bold">
      {title}
    </Text>
    <Button size="2xs" variant="outline" onClick={onCreate}>
      <FiPlus />
      {actionLabel}
    </Button>
  </Flex>
)

export const WorkspaceSidebar = ({
  boards,
  notes,
  onCreateBoard,
  onCreateNote,
  onDelete,
  onSelect,
  selection,
}: {
  boards: KanbanBoard[]
  notes: Note[]
  onCreateBoard: () => void
  onCreateNote: () => void
  onDelete: (kind: WorkspaceItemKind, id: string) => void
  onSelect: (kind: WorkspaceItemKind, id: string) => void
  selection: WorkspaceSelection
}) => {
  const { i18n, t } = useTranslation("notes")
  const [confirmingDeleteId, setConfirmingDeleteId] = useState<string | null>(
    null,
  )

  useEffect(() => {
    setConfirmingDeleteId(null)
  }, [])

  const language = i18n.resolvedLanguage ?? i18n.language

  const formatItemDate = (value: string) =>
    formatDate(new Date(value), language, {
      day: "2-digit",
      month: "short",
    }) ?? value

  const handleDeleteClick = (kind: WorkspaceItemKind, id: string) => {
    if (confirmingDeleteId === id) {
      setConfirmingDeleteId(null)
      onDelete(kind, id)
      return
    }
    setConfirmingDeleteId(id)
  }

  const handleSelect = (kind: WorkspaceItemKind, id: string) => {
    setConfirmingDeleteId(null)
    onSelect(kind, id)
  }

  return (
    <Flex direction="column" gap={5} p={{ base: 4, md: 4 }}>
      <Flex direction="column" gap={2}>
        <SectionHeader
          actionLabel={t("sidebar.newNote")}
          title={t("sidebar.notesSection")}
          onCreate={onCreateNote}
        />
        {notes.length === 0 ? (
          <Text color="ui.secondaryText" fontSize="xs" px={1}>
            {t("sidebar.emptyNotes")}
          </Text>
        ) : (
          notes.map((note) => (
            <SidebarItem
              key={note.id}
              isConfirmingDelete={confirmingDeleteId === note.id}
              isSelected={
                selection?.kind === "note" && selection.id === note.id
              }
              meta={[formatItemDate(note.createdAt), note.tag]
                .filter(Boolean)
                .join(" · ")}
              title={note.title || t("note.untitled")}
              onDelete={() => handleDeleteClick("note", note.id)}
              onSelect={() => handleSelect("note", note.id)}
            />
          ))
        )}
      </Flex>

      <Flex direction="column" gap={2}>
        <SectionHeader
          actionLabel={t("sidebar.newBoard")}
          title={t("sidebar.boardsSection")}
          onCreate={onCreateBoard}
        />
        {boards.length === 0 ? (
          <Text color="ui.secondaryText" fontSize="xs" px={1}>
            {t("sidebar.emptyBoards")}
          </Text>
        ) : (
          boards.map((board) => (
            <SidebarItem
              key={board.id}
              isConfirmingDelete={confirmingDeleteId === board.id}
              isSelected={
                selection?.kind === "board" && selection.id === board.id
              }
              meta={`${formatItemDate(board.createdAt)} · ${t(
                "kanban.tasksCount",
                {
                  count: board.columns.reduce(
                    (total, column) => total + column.tasks.length,
                    0,
                  ),
                },
              )}`}
              title={board.title || t("kanban.untitled")}
              onDelete={() => handleDeleteClick("board", board.id)}
              onSelect={() => handleSelect("board", board.id)}
            />
          ))
        )}
      </Flex>
    </Flex>
  )
}
