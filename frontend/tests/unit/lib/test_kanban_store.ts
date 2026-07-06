import { beforeEach, describe, expect, test, vi } from "vitest"

import {
  KANBAN_BOARDS_STORAGE_KEY,
  type KanbanBoard,
  MAX_KANBAN_COLUMNS,
  readKanbanBoards,
  removeKanbanBoard,
  subscribeToKanbanBoards,
  upsertKanbanBoard,
} from "../../../src/lib/kanban-store"

const createBoard = (overrides: Partial<KanbanBoard> = {}): KanbanBoard => ({
  id: "board-1",
  title: "Launch plan",
  createdAt: "2026-07-07T00:00:00Z",
  updatedAt: "2026-07-07T00:00:00Z",
  columns: [
    {
      id: "column-1",
      name: "To Do",
      tasks: [
        {
          id: "task-1",
          title: "Draft brief",
          createdAt: "2026-07-07T00:00:00Z",
          updatedAt: "2026-07-07T00:00:00Z",
        },
      ],
    },
    { id: "column-2", name: "Done", tasks: [] },
  ],
  ...overrides,
})

describe("kanban store", () => {
  beforeEach(() => {
    localStorage.clear()
  })

  test("kanban_store_corrupt_storage_returns_empty_list", () => {
    // Arrange
    localStorage.setItem(KANBAN_BOARDS_STORAGE_KEY, "{not-json")

    // Act / Assert
    expect(readKanbanBoards()).toEqual([])
  })

  test("kanban_store_boards_beyond_column_cap_are_dropped", () => {
    // Arrange
    const overloadedBoard = createBoard({
      id: "board-overloaded",
      columns: Array.from({ length: MAX_KANBAN_COLUMNS + 1 }, (_, index) => ({
        id: `column-${index}`,
        name: `Stage ${index}`,
        tasks: [],
      })),
    })
    localStorage.setItem(
      KANBAN_BOARDS_STORAGE_KEY,
      JSON.stringify([createBoard(), overloadedBoard]),
    )

    // Act
    const boards = readKanbanBoards()

    // Assert
    expect(boards.map((board) => board.id)).toEqual(["board-1"])
  })

  test("kanban_store_malformed_tasks_drop_the_board", () => {
    // Arrange
    localStorage.setItem(
      KANBAN_BOARDS_STORAGE_KEY,
      JSON.stringify([
        createBoard({
          id: "board-broken",
          columns: [{ id: "c", name: "To Do", tasks: [{ id: 42 }] }],
        }),
      ]),
    )

    // Act / Assert
    expect(readKanbanBoards()).toEqual([])
  })

  test("kanban_store_upsert_replaces_existing_and_prepends", () => {
    // Arrange
    upsertKanbanBoard(createBoard())
    upsertKanbanBoard(createBoard({ id: "board-2", title: "Q3 roadmap" }))

    // Act
    const boards = upsertKanbanBoard(createBoard({ title: "Launch plan v2" }))

    // Assert
    expect(boards.map((board) => board.id)).toEqual(["board-1", "board-2"])
    expect(boards[0].title).toBe("Launch plan v2")
  })

  test("kanban_store_remove_deletes_by_id", () => {
    // Arrange
    upsertKanbanBoard(createBoard())

    // Act
    const boards = removeKanbanBoard("board-1")

    // Assert
    expect(boards).toEqual([])
    expect(readKanbanBoards()).toEqual([])
  })

  test("kanban_store_subscribe_receives_updates_and_unsubscribes", () => {
    // Arrange
    const listener = vi.fn()
    const unsubscribe = subscribeToKanbanBoards(listener)

    // Act
    upsertKanbanBoard(createBoard())

    // Assert
    expect(listener).toHaveBeenCalledWith(
      expect.arrayContaining([expect.objectContaining({ id: "board-1" })]),
    )

    // Act
    unsubscribe()
    upsertKanbanBoard(createBoard({ id: "board-2" }))

    // Assert
    expect(listener).toHaveBeenCalledTimes(1)
  })
})
