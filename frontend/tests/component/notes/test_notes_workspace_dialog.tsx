import { act, fireEvent, screen, within } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import { beforeEach, describe, expect, test } from "vitest"

import { NotesWorkspaceButton } from "../../../src/components/Notes/NotesWorkspaceButton"
import { KANBAN_BOARDS_STORAGE_KEY } from "../../../src/lib/kanban-store"
import { NOTES_STORAGE_KEY, readNotes } from "../../../src/lib/notes-store"
import { renderWithProviders } from "../helpers/render"

const openWorkspace = async (user: ReturnType<typeof userEvent.setup>) => {
  renderWithProviders(<NotesWorkspaceButton />, { language: "en" })
  await user.click(screen.getByRole("button", { name: "Notes and boards" }))
  expect(await screen.findByText("Your notes and tasks space")).toBeVisible()
}

const createNote = async (user: ReturnType<typeof userEvent.setup>) => {
  await user.click(screen.getByRole("button", { name: "New note" }))
  expect(await screen.findByPlaceholderText("Note title...")).toBeVisible()
}

const createBoard = async (user: ReturnType<typeof userEvent.setup>) => {
  await user.click(screen.getByRole("button", { name: "New board" }))
  expect(await screen.findByPlaceholderText("Board title...")).toBeVisible()
}

describe("notes workspace dialog", () => {
  beforeEach(() => {
    localStorage.removeItem(NOTES_STORAGE_KEY)
    localStorage.removeItem(KANBAN_BOARDS_STORAGE_KEY)
  })

  test("notes_workspace_create_note_persists_title_and_tag", async () => {
    // Arrange
    const user = userEvent.setup()
    await openWorkspace(user)

    // Act
    await createNote(user)
    await user.type(screen.getByPlaceholderText("Note title..."), "Weekly sync")
    await user.click(screen.getByRole("button", { name: "Meeting" }))

    // Assert
    const notes = readNotes()
    expect(notes).toHaveLength(1)
    expect(notes[0].title).toBe("Weekly sync")
    expect(notes[0].tag).toBe("Meeting")
    expect(notes[0].createdAt).toBeTruthy()
  })

  test("notes_workspace_enter_adds_line_and_tab_indents", async () => {
    // Arrange
    const user = userEvent.setup()
    await openWorkspace(user)
    await createNote(user)
    const firstLine = screen.getByPlaceholderText("Write something...")

    // Act
    await user.type(firstLine, "Parent item")
    await user.keyboard("{Enter}")

    // Assert
    const blocks = screen.getAllByTestId("note-block")
    expect(blocks).toHaveLength(2)

    // Act: indent the new line, then outdent it back.
    const secondInput = within(blocks[1]).getByPlaceholderText(
      "Write something...",
    )
    await act(async () => {
      fireEvent.keyDown(secondInput, { key: "Tab" })
      await Promise.resolve()
    })

    // Assert
    expect(screen.getAllByTestId("note-block")[1]).toHaveAttribute(
      "data-indent",
      "1",
    )
    expect(readNotes()[0].blocks[1].indent).toBe(1)

    // Act
    const indentedSecondInput = within(
      screen.getAllByTestId("note-block")[1],
    ).getByPlaceholderText("Write something...")
    await act(async () => {
      fireEvent.keyDown(indentedSecondInput, { key: "Tab", shiftKey: true })
      await Promise.resolve()
    })

    // Assert
    expect(screen.getAllByTestId("note-block")[1]).toHaveAttribute(
      "data-indent",
      "0",
    )
  })

  test("notes_workspace_backspace_on_empty_line_removes_it", async () => {
    // Arrange
    const user = userEvent.setup()
    await openWorkspace(user)
    await createNote(user)
    await user.type(
      screen.getByPlaceholderText("Write something..."),
      "Only line",
    )
    await user.keyboard("{Enter}")
    expect(screen.getAllByTestId("note-block")).toHaveLength(2)

    // Act: the new empty line is focused; backspace removes it.
    await user.keyboard("{Backspace}")

    // Assert
    expect(screen.getAllByTestId("note-block")).toHaveLength(1)
    expect(readNotes()[0].blocks).toHaveLength(1)
  })

  test("notes_workspace_line_type_cycles_to_check_and_toggles", async () => {
    // Arrange
    const user = userEvent.setup()
    await openWorkspace(user)
    await createNote(user)

    // Act: text → bullet → check.
    const typeToggle = screen.getByRole("button", {
      name: "Change line type",
    })
    await user.click(typeToggle)
    await user.click(typeToggle)
    await user.click(screen.getByRole("checkbox", { name: "Mark as done" }))

    // Assert
    const blocks = readNotes()[0].blocks
    expect(blocks[0].type).toBe("check")
    expect(blocks[0].checked).toBe(true)
  })

  test("notes_workspace_delete_note_requires_two_step_confirm", async () => {
    // Arrange
    const user = userEvent.setup()
    await openWorkspace(user)
    await createNote(user)

    // Act
    await user.click(screen.getByRole("button", { name: "Delete" }))
    await user.click(screen.getByRole("button", { name: "Confirm?" }))

    // Assert
    expect(readNotes()).toHaveLength(0)
    expect(screen.getByText("No notes yet.")).toBeVisible()
    expect(screen.getByText("Your notes and tasks space")).toBeVisible()
  })

  test("notes_workspace_new_board_starts_with_preset_columns", async () => {
    // Arrange
    const user = userEvent.setup()
    await openWorkspace(user)

    // Act
    await createBoard(user)

    // Assert
    expect(screen.getByDisplayValue("To Do")).toBeVisible()
    expect(screen.getByDisplayValue("In Progress")).toBeVisible()
    expect(screen.getByDisplayValue("Review")).toBeVisible()
    expect(screen.getByDisplayValue("Done")).toBeVisible()
    expect(screen.getAllByTestId("kanban-column")).toHaveLength(4)
  })

  test("notes_workspace_add_column_caps_at_eight", async () => {
    // Arrange
    const user = userEvent.setup()
    await openWorkspace(user)
    await createBoard(user)
    const addColumn = screen.getByRole("button", { name: "Add column" })

    // Act
    await user.click(addColumn)
    await user.click(addColumn)
    await user.click(addColumn)
    await user.click(addColumn)

    // Assert
    expect(screen.getAllByTestId("kanban-column")).toHaveLength(8)
    expect(addColumn).toBeDisabled()
    expect(screen.getByText("Max 8 columns")).toBeVisible()
  })

  test("notes_workspace_task_moves_right_with_fallback_button", async () => {
    // Arrange
    const user = userEvent.setup()
    await openWorkspace(user)
    await createBoard(user)
    const firstColumn = screen.getAllByTestId("kanban-column")[0]
    await user.type(
      within(firstColumn).getByPlaceholderText("Task title..."),
      "Draft brief{Enter}",
    )
    expect(within(firstColumn).getByDisplayValue("Draft brief")).toBeVisible()

    // Act
    await user.click(screen.getByRole("button", { name: "Move right" }))

    // Assert
    const columns = screen.getAllByTestId("kanban-column")
    expect(within(columns[1]).getByDisplayValue("Draft brief")).toBeVisible()
    expect(within(columns[0]).queryByDisplayValue("Draft brief")).toBeNull()
  })

  test("notes_workspace_task_moves_between_columns_with_drag_and_drop", async () => {
    // Arrange
    const user = userEvent.setup()
    await openWorkspace(user)
    await createBoard(user)
    const firstColumn = screen.getAllByTestId("kanban-column")[0]
    await user.type(
      within(firstColumn).getByPlaceholderText("Task title..."),
      "Ship it{Enter}",
    )

    // Act
    fireEvent.dragStart(screen.getByTestId("kanban-task"))
    const targetColumn = screen.getAllByTestId("kanban-column")[2]
    fireEvent.dragOver(targetColumn)
    fireEvent.drop(targetColumn)

    // Assert
    expect(
      within(screen.getAllByTestId("kanban-column")[2]).getByDisplayValue(
        "Ship it",
      ),
    ).toBeVisible()
  })

  test("notes_workspace_delete_column_with_tasks_requires_confirm", async () => {
    // Arrange
    const user = userEvent.setup()
    await openWorkspace(user)
    await createBoard(user)
    const firstColumn = screen.getAllByTestId("kanban-column")[0]
    await user.type(
      within(firstColumn).getByPlaceholderText("Task title..."),
      "Pending task{Enter}",
    )

    // Act: first click arms the confirmation, second click deletes.
    await user.click(
      within(firstColumn).getByRole("button", { name: "Delete column" }),
    )
    await user.click(
      within(firstColumn).getByRole("button", { name: "Delete column" }),
    )

    // Assert
    expect(screen.getAllByTestId("kanban-column")).toHaveLength(3)
    expect(screen.queryByDisplayValue("To Do")).toBeNull()
  })
})
