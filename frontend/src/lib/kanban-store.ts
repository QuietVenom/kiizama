export const KANBAN_BOARDS_STORAGE_KEY = "kiizama-kanban-boards"
export const KANBAN_BOARDS_UPDATED_EVENT = "kiizama-kanban-boards-updated"

export const MAX_KANBAN_COLUMNS = 8

export type KanbanTask = {
  id: string
  title: string
  description?: string
  createdAt: string
  updatedAt: string
}

export type KanbanColumn = {
  id: string
  name: string
  tasks: KanbanTask[]
}

export type KanbanBoard = {
  id: string
  title: string
  createdAt: string
  updatedAt: string
  columns: KanbanColumn[]
}

type KanbanBoardsUpdatedDetail = {
  boards: KanbanBoard[]
}

const isRecord = (value: unknown): value is Record<string, unknown> =>
  typeof value === "object" && value !== null && !Array.isArray(value)

const isKanbanTask = (value: unknown): value is KanbanTask => {
  if (!isRecord(value)) {
    return false
  }

  return (
    typeof value.id === "string" &&
    typeof value.title === "string" &&
    (value.description === undefined ||
      typeof value.description === "string") &&
    typeof value.createdAt === "string" &&
    typeof value.updatedAt === "string"
  )
}

const isKanbanColumn = (value: unknown): value is KanbanColumn => {
  if (!isRecord(value)) {
    return false
  }

  return (
    typeof value.id === "string" &&
    typeof value.name === "string" &&
    Array.isArray(value.tasks) &&
    value.tasks.every(isKanbanTask)
  )
}

const isKanbanBoard = (value: unknown): value is KanbanBoard => {
  if (!isRecord(value)) {
    return false
  }

  return (
    typeof value.id === "string" &&
    typeof value.title === "string" &&
    typeof value.createdAt === "string" &&
    typeof value.updatedAt === "string" &&
    Array.isArray(value.columns) &&
    value.columns.length <= MAX_KANBAN_COLUMNS &&
    value.columns.every(isKanbanColumn)
  )
}

const dispatchKanbanBoardsUpdated = (boards: KanbanBoard[]) => {
  if (typeof window === "undefined") {
    return
  }

  window.dispatchEvent(
    new CustomEvent<KanbanBoardsUpdatedDetail>(KANBAN_BOARDS_UPDATED_EVENT, {
      detail: { boards },
    }),
  )
}

const persistKanbanBoards = (boards: KanbanBoard[]) => {
  if (typeof window === "undefined") {
    return boards
  }

  localStorage.setItem(KANBAN_BOARDS_STORAGE_KEY, JSON.stringify(boards))
  dispatchKanbanBoardsUpdated(boards)
  return boards
}

export const readKanbanBoards = (): KanbanBoard[] => {
  if (typeof window === "undefined") {
    return []
  }

  try {
    const rawValue = localStorage.getItem(KANBAN_BOARDS_STORAGE_KEY)
    if (!rawValue) {
      return []
    }

    const parsed: unknown = JSON.parse(rawValue)
    if (!Array.isArray(parsed)) {
      return []
    }

    return parsed.filter(isKanbanBoard)
  } catch {
    return []
  }
}

export const upsertKanbanBoard = (board: KanbanBoard) => {
  const currentBoards = readKanbanBoards()
  const nextBoards = currentBoards.filter(
    (currentBoard) => currentBoard.id !== board.id,
  )
  nextBoards.unshift(board)
  return persistKanbanBoards(nextBoards)
}

export const removeKanbanBoard = (boardId: string) => {
  const nextBoards = readKanbanBoards().filter((board) => board.id !== boardId)
  return persistKanbanBoards(nextBoards)
}

export const subscribeToKanbanBoards = (
  listener: (boards: KanbanBoard[]) => void,
) => {
  if (typeof window === "undefined") {
    return () => {}
  }

  const handleUpdated = (event: Event) => {
    const detail = (event as CustomEvent<KanbanBoardsUpdatedDetail>).detail
    listener(detail?.boards ?? readKanbanBoards())
  }

  const handleStorage = (event: StorageEvent) => {
    if (event.key === KANBAN_BOARDS_STORAGE_KEY) {
      listener(readKanbanBoards())
    }
  }

  window.addEventListener(KANBAN_BOARDS_UPDATED_EVENT, handleUpdated)
  window.addEventListener("storage", handleStorage)

  return () => {
    window.removeEventListener(KANBAN_BOARDS_UPDATED_EVENT, handleUpdated)
    window.removeEventListener("storage", handleStorage)
  }
}
