import { Box, Flex, Heading, Text } from "@chakra-ui/react"
import { useEffect, useState } from "react"
import { useTranslation } from "react-i18next"
import { LuNotebookPen } from "react-icons/lu"

import {
  DialogBody,
  DialogCloseTrigger,
  DialogContent,
  DialogHeader,
  DialogRoot,
  DialogTitle,
} from "@/components/ui/dialog"
import {
  type KanbanBoard,
  readKanbanBoards,
  removeKanbanBoard,
  subscribeToKanbanBoards,
  upsertKanbanBoard,
} from "@/lib/kanban-store"
import {
  type Note,
  readNotes,
  removeNote,
  subscribeToNotes,
  upsertNote,
} from "@/lib/notes-store"
import { uuidv7 } from "@/lib/uuidv7"

import { KanbanBoardView } from "./KanbanBoardView"
import { NoteEditor } from "./NoteEditor"
import { WorkspaceSidebar } from "./WorkspaceSidebar"

export type WorkspaceSelection = {
  kind: "note" | "board"
  id: string
} | null

const KANBAN_PRESET_KEYS = ["todo", "inProgress", "review", "done"] as const

export const NotesWorkspaceDialog = ({
  open,
  onOpenChange,
}: {
  open: boolean
  onOpenChange: (open: boolean) => void
}) => {
  const { t } = useTranslation("notes")
  const [notes, setNotes] = useState<Note[]>(() => readNotes())
  const [boards, setBoards] = useState<KanbanBoard[]>(() => readKanbanBoards())
  const [selection, setSelection] = useState<WorkspaceSelection>(null)

  useEffect(() => subscribeToNotes(setNotes), [])
  useEffect(() => subscribeToKanbanBoards(setBoards), [])

  const selectedNote =
    selection?.kind === "note"
      ? (notes.find((note) => note.id === selection.id) ?? null)
      : null
  const selectedBoard =
    selection?.kind === "board"
      ? (boards.find((board) => board.id === selection.id) ?? null)
      : null

  const handleCreateNote = () => {
    const now = new Date().toISOString()
    const note: Note = {
      id: uuidv7(),
      title: "",
      tag: null,
      createdAt: now,
      updatedAt: now,
      blocks: [{ id: uuidv7(), type: "text", indent: 0, text: "" }],
    }
    upsertNote(note)
    setSelection({ kind: "note", id: note.id })
  }

  const handleCreateBoard = () => {
    const now = new Date().toISOString()
    const board: KanbanBoard = {
      id: uuidv7(),
      title: "",
      createdAt: now,
      updatedAt: now,
      columns: KANBAN_PRESET_KEYS.map((presetKey) => ({
        id: uuidv7(),
        name: t(`kanban.presets.${presetKey}`),
        tasks: [],
      })),
    }
    upsertKanbanBoard(board)
    setSelection({ kind: "board", id: board.id })
  }

  const handleDelete = (kind: "note" | "board", id: string) => {
    if (kind === "note") {
      removeNote(id)
    } else {
      removeKanbanBoard(id)
    }
    if (selection?.kind === kind && selection.id === id) {
      setSelection(null)
    }
  }

  const handleNoteChange = (note: Note) => {
    upsertNote({ ...note, updatedAt: new Date().toISOString() })
  }

  const handleBoardChange = (board: KanbanBoard) => {
    upsertKanbanBoard({ ...board, updatedAt: new Date().toISOString() })
  }

  return (
    <DialogRoot
      open={open}
      placement="center"
      onOpenChange={({ open: nextOpen }) => onOpenChange(nextOpen)}
    >
      <DialogContent
        display="flex"
        flexDirection="column"
        w={{ base: "calc(100vw - 1rem)", md: "75vw" }}
        maxW={{ base: "calc(100vw - 1rem)", md: "75vw" }}
        h={{ base: "calc(100vh - 1rem)", md: "75vh" }}
        maxH={{ base: "calc(100vh - 1rem)", md: "75vh" }}
        overflow="hidden"
        rounded="4xl"
        borderWidth="1px"
        borderColor="ui.border"
        bg="ui.page"
      >
        <DialogCloseTrigger />
        <DialogHeader
          borderBottomWidth="1px"
          borderBottomColor="ui.border"
          bg="ui.panel"
          px={{ base: 5, md: 6 }}
          py={{ base: 4, md: 5 }}
        >
          <DialogTitle
            display="inline-flex"
            alignItems="center"
            gap={2.5}
            fontSize={{ base: "lg", md: "xl" }}
            fontWeight="black"
            letterSpacing="-0.02em"
          >
            <LuNotebookPen />
            {t("dialog.title")}
          </DialogTitle>
        </DialogHeader>

        <DialogBody p={0} flex="1" overflow="hidden">
          <Flex h="full" direction={{ base: "column", md: "row" }}>
            <Box
              w={{ base: "full", md: "280px" }}
              maxH={{ base: "40%", md: "full" }}
              flexShrink={0}
              borderRightWidth={{ base: 0, md: "1px" }}
              borderBottomWidth={{ base: "1px", md: 0 }}
              borderColor="ui.border"
              bg="ui.panel"
              overflowY="auto"
            >
              <WorkspaceSidebar
                boards={boards}
                notes={notes}
                selection={selection}
                onCreateBoard={handleCreateBoard}
                onCreateNote={handleCreateNote}
                onDelete={handleDelete}
                onSelect={(kind, id) => setSelection({ kind, id })}
              />
            </Box>

            <Box flex="1" minW={0} overflowY="auto" p={{ base: 4, md: 6 }}>
              {selectedNote ? (
                <NoteEditor note={selectedNote} onChange={handleNoteChange} />
              ) : selectedBoard ? (
                <KanbanBoardView
                  board={selectedBoard}
                  onChange={handleBoardChange}
                />
              ) : (
                <Flex
                  h="full"
                  direction="column"
                  align="center"
                  justify="center"
                  textAlign="center"
                  px={6}
                >
                  <Flex
                    boxSize="12"
                    rounded="full"
                    align="center"
                    justify="center"
                    bg="ui.brandSoft"
                    color="ui.brandText"
                  >
                    <LuNotebookPen size={20} />
                  </Flex>
                  <Heading mt={4} fontSize="xl">
                    {t("dialog.empty.title")}
                  </Heading>
                  <Text mt={2} color="ui.secondaryText" maxW="46ch">
                    {t("dialog.empty.description")}
                  </Text>
                </Flex>
              )}
            </Box>
          </Flex>
        </DialogBody>
      </DialogContent>
    </DialogRoot>
  )
}
