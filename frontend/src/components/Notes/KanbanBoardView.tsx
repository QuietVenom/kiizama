import { Box, Flex, IconButton, Input, Text, Textarea } from "@chakra-ui/react"
import { type DragEvent, useRef, useState } from "react"
import { useTranslation } from "react-i18next"
import { FiChevronLeft, FiChevronRight, FiPlus, FiTrash2 } from "react-icons/fi"

import { Button } from "@/components/ui/button"
import {
  type KanbanBoard,
  type KanbanColumn,
  type KanbanTask,
  MAX_KANBAN_COLUMNS,
} from "@/lib/kanban-store"
import { uuidv7 } from "@/lib/uuidv7"

type DragSource = {
  taskId: string
  fromColumnId: string
}

const AddTaskRow = ({ onAdd }: { onAdd: (title: string) => void }) => {
  const { t } = useTranslation("notes")
  const [draft, setDraft] = useState("")

  const submit = () => {
    const title = draft.trim()
    if (!title) {
      return
    }
    onAdd(title)
    setDraft("")
  }

  return (
    <Flex mt={2.5} align="center" gap={1.5}>
      <Input
        value={draft}
        placeholder={t("kanban.taskTitlePlaceholder")}
        size="sm"
        rounded="14px"
        bg="ui.panel"
        onChange={(event) => setDraft(event.target.value)}
        onKeyDown={(event) => {
          if (event.key === "Enter") {
            event.preventDefault()
            submit()
          }
        }}
      />
      <IconButton
        aria-label={t("kanban.addTask")}
        size="sm"
        variant="outline"
        disabled={draft.trim() === ""}
        onClick={submit}
      >
        <FiPlus />
      </IconButton>
    </Flex>
  )
}

export const KanbanBoardView = ({
  board,
  onChange,
}: {
  board: KanbanBoard
  onChange: (board: KanbanBoard) => void
}) => {
  const { t } = useTranslation("notes")
  const [confirmingColumnId, setConfirmingColumnId] = useState<string | null>(
    null,
  )
  const dragSourceRef = useRef<DragSource | null>(null)

  const patchColumns = (columns: KanbanColumn[]) => {
    onChange({ ...board, columns })
  }

  const updateColumn = (columnId: string, patch: Partial<KanbanColumn>) => {
    patchColumns(
      board.columns.map((column) =>
        column.id === columnId ? { ...column, ...patch } : column,
      ),
    )
  }

  const addColumn = () => {
    if (board.columns.length >= MAX_KANBAN_COLUMNS) {
      return
    }
    patchColumns([...board.columns, { id: uuidv7(), name: "", tasks: [] }])
  }

  const deleteColumn = (column: KanbanColumn) => {
    if (column.tasks.length > 0 && confirmingColumnId !== column.id) {
      setConfirmingColumnId(column.id)
      return
    }
    setConfirmingColumnId(null)
    patchColumns(board.columns.filter((current) => current.id !== column.id))
  }

  const addTask = (columnId: string, title: string) => {
    const now = new Date().toISOString()
    const task: KanbanTask = {
      id: uuidv7(),
      title,
      createdAt: now,
      updatedAt: now,
    }
    patchColumns(
      board.columns.map((column) =>
        column.id === columnId
          ? { ...column, tasks: [...column.tasks, task] }
          : column,
      ),
    )
  }

  const updateTask = (
    columnId: string,
    taskId: string,
    patch: Partial<KanbanTask>,
  ) => {
    patchColumns(
      board.columns.map((column) =>
        column.id === columnId
          ? {
              ...column,
              tasks: column.tasks.map((task) =>
                task.id === taskId
                  ? { ...task, ...patch, updatedAt: new Date().toISOString() }
                  : task,
              ),
            }
          : column,
      ),
    )
  }

  const deleteTask = (columnId: string, taskId: string) => {
    patchColumns(
      board.columns.map((column) =>
        column.id === columnId
          ? {
              ...column,
              tasks: column.tasks.filter((task) => task.id !== taskId),
            }
          : column,
      ),
    )
  }

  const moveTask = (
    source: DragSource,
    toColumnId: string,
    targetIndex: number | null,
  ) => {
    const fromColumn = board.columns.find(
      (column) => column.id === source.fromColumnId,
    )
    const task = fromColumn?.tasks.find(
      (currentTask) => currentTask.id === source.taskId,
    )
    if (!fromColumn || !task) {
      return
    }

    const columnsWithoutTask = board.columns.map((column) =>
      column.id === source.fromColumnId
        ? {
            ...column,
            tasks: column.tasks.filter(
              (currentTask) => currentTask.id !== source.taskId,
            ),
          }
        : column,
    )

    patchColumns(
      columnsWithoutTask.map((column) => {
        if (column.id !== toColumnId) {
          return column
        }
        const tasks = [...column.tasks]
        tasks.splice(targetIndex ?? tasks.length, 0, task)
        return { ...column, tasks }
      }),
    )
  }

  const moveTaskToAdjacent = (
    columnIndex: number,
    task: KanbanTask,
    direction: -1 | 1,
  ) => {
    const targetColumn = board.columns[columnIndex + direction]
    if (!targetColumn) {
      return
    }
    moveTask(
      { taskId: task.id, fromColumnId: board.columns[columnIndex].id },
      targetColumn.id,
      null,
    )
  }

  const handleDrop = (
    event: DragEvent,
    toColumnId: string,
    targetIndex: number | null,
  ) => {
    event.preventDefault()
    event.stopPropagation()
    const source = dragSourceRef.current
    dragSourceRef.current = null
    if (!source) {
      return
    }
    moveTask(source, toColumnId, targetIndex)
  }

  return (
    <Box>
      <Input
        value={board.title}
        placeholder={t("kanban.titlePlaceholder")}
        variant="flushed"
        fontSize="2xl"
        fontWeight="black"
        letterSpacing="-0.02em"
        onChange={(event) => onChange({ ...board, title: event.target.value })}
      />

      <Flex mt={5} gap={4} align="flex-start" overflowX="auto" pb={2}>
        {board.columns.map((column, columnIndex) => (
          <Box
            key={column.id}
            w="280px"
            flexShrink={0}
            rounded="24px"
            borderWidth="1px"
            borderColor="ui.borderSoft"
            bg="ui.surfaceSoft"
            p={3.5}
            data-testid="kanban-column"
            onDragOver={(event) => event.preventDefault()}
            onDrop={(event) => handleDrop(event, column.id, null)}
          >
            <Flex align="center" gap={1.5}>
              <Input
                value={column.name}
                placeholder={t("kanban.columnNamePlaceholder")}
                variant="flushed"
                size="sm"
                fontWeight="black"
                onChange={(event) =>
                  updateColumn(column.id, { name: event.target.value })
                }
              />
              <Text
                color="ui.mutedText"
                fontSize="xs"
                fontWeight="bold"
                whiteSpace="nowrap"
              >
                {column.tasks.length}
              </Text>
              <Button
                size="2xs"
                variant={confirmingColumnId === column.id ? "solid" : "ghost"}
                colorPalette={
                  confirmingColumnId === column.id ? "red" : undefined
                }
                color={
                  confirmingColumnId === column.id ? undefined : "ui.mutedText"
                }
                flexShrink={0}
                aria-label={t("kanban.deleteColumn")}
                onClick={() => deleteColumn(column)}
              >
                {confirmingColumnId === column.id ? (
                  t("kanban.confirmDelete")
                ) : (
                  <FiTrash2 />
                )}
              </Button>
            </Flex>

            <Flex mt={3} direction="column" gap={2.5}>
              {column.tasks.map((task, taskIndex) => (
                <Box
                  key={task.id}
                  draggable
                  cursor="grab"
                  rounded="18px"
                  borderWidth="1px"
                  borderColor="ui.border"
                  bg="ui.panel"
                  boxShadow="ui.card"
                  p={3}
                  data-testid="kanban-task"
                  onDragStart={() => {
                    dragSourceRef.current = {
                      taskId: task.id,
                      fromColumnId: column.id,
                    }
                  }}
                  onDragEnd={() => {
                    dragSourceRef.current = null
                  }}
                  onDragOver={(event) => event.preventDefault()}
                  onDrop={(event) => handleDrop(event, column.id, taskIndex)}
                >
                  <Input
                    value={task.title}
                    placeholder={t("kanban.taskTitlePlaceholder")}
                    variant="flushed"
                    size="sm"
                    fontWeight="bold"
                    onChange={(event) =>
                      updateTask(column.id, task.id, {
                        title: event.target.value,
                      })
                    }
                  />
                  <Textarea
                    mt={1.5}
                    value={task.description ?? ""}
                    placeholder={t("kanban.taskDescriptionPlaceholder")}
                    size="xs"
                    variant="subtle"
                    rows={1}
                    bg="transparent"
                    color="ui.secondaryText"
                    onChange={(event) =>
                      updateTask(column.id, task.id, {
                        description: event.target.value,
                      })
                    }
                  />
                  <Flex mt={2} align="center" justify="space-between" gap={1}>
                    <Flex align="center" gap={1}>
                      <IconButton
                        aria-label={t("kanban.moveLeft")}
                        size="2xs"
                        variant="ghost"
                        color="ui.mutedText"
                        visibility={columnIndex === 0 ? "hidden" : "visible"}
                        onClick={() =>
                          moveTaskToAdjacent(columnIndex, task, -1)
                        }
                      >
                        <FiChevronLeft />
                      </IconButton>
                      <IconButton
                        aria-label={t("kanban.moveRight")}
                        size="2xs"
                        variant="ghost"
                        color="ui.mutedText"
                        visibility={
                          columnIndex === board.columns.length - 1
                            ? "hidden"
                            : "visible"
                        }
                        onClick={() => moveTaskToAdjacent(columnIndex, task, 1)}
                      >
                        <FiChevronRight />
                      </IconButton>
                    </Flex>
                    <IconButton
                      aria-label={t("kanban.deleteTask")}
                      size="2xs"
                      variant="ghost"
                      color="ui.mutedText"
                      onClick={() => deleteTask(column.id, task.id)}
                    >
                      <FiTrash2 />
                    </IconButton>
                  </Flex>
                </Box>
              ))}
            </Flex>

            <AddTaskRow onAdd={(title) => addTask(column.id, title)} />
          </Box>
        ))}

        <Box flexShrink={0} pt={1}>
          <Button
            size="sm"
            variant="outline"
            disabled={board.columns.length >= MAX_KANBAN_COLUMNS}
            onClick={addColumn}
          >
            <FiPlus />
            {t("kanban.addColumn")}
          </Button>
          {board.columns.length >= MAX_KANBAN_COLUMNS ? (
            <Text mt={2} color="ui.mutedText" fontSize="xs">
              {t("kanban.columnLimit", { max: MAX_KANBAN_COLUMNS })}
            </Text>
          ) : null}
        </Box>
      </Flex>
    </Box>
  )
}
