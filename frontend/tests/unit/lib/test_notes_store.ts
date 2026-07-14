import { beforeEach, describe, expect, test, vi } from "vitest"

import {
  NOTES_STORAGE_KEY,
  NOTES_UPDATED_EVENT,
  type Note,
  readNotes,
  removeNote,
  subscribeToNotes,
  upsertNote,
} from "../../../src/lib/notes-store"

const createNote = (overrides: Partial<Note> = {}): Note => ({
  id: "note-1",
  title: "Weekly sync",
  tag: "work",
  createdAt: "2026-07-07T00:00:00Z",
  updatedAt: "2026-07-07T00:00:00Z",
  blocks: [
    {
      id: "block-1",
      type: "check",
      indent: 0,
      text: "Prepare agenda",
      checked: false,
    },
  ],
  ...overrides,
})

describe("notes store", () => {
  beforeEach(() => {
    localStorage.clear()
  })

  test("notes_store_corrupt_storage_returns_empty_list", () => {
    // Arrange
    localStorage.setItem(NOTES_STORAGE_KEY, "{not-json")

    // Act / Assert
    expect(readNotes()).toEqual([])
  })

  test("notes_store_malformed_entries_are_dropped", () => {
    // Arrange
    localStorage.setItem(
      NOTES_STORAGE_KEY,
      JSON.stringify([
        createNote(),
        { id: "broken", title: 42 },
        createNote({
          id: "note-bad-block",
          blocks: [{ id: "b", type: "check", indent: 9, text: "x" }],
        }),
      ]),
    )

    // Act
    const notes = readNotes()

    // Assert
    expect(notes).toHaveLength(1)
    expect(notes[0].id).toBe("note-1")
  })

  test("notes_store_upsert_replaces_existing_and_prepends", () => {
    // Arrange
    upsertNote(createNote())
    upsertNote(createNote({ id: "note-2", title: "Ideas dump" }))

    // Act
    const notes = upsertNote(createNote({ title: "Weekly sync v2" }))

    // Assert
    expect(notes.map((note) => note.id)).toEqual(["note-1", "note-2"])
    expect(notes[0].title).toBe("Weekly sync v2")
  })

  test("notes_store_remove_deletes_by_id", () => {
    // Arrange
    upsertNote(createNote())
    upsertNote(createNote({ id: "note-2" }))

    // Act
    const notes = removeNote("note-1")

    // Assert
    expect(notes.map((note) => note.id)).toEqual(["note-2"])
    expect(readNotes().map((note) => note.id)).toEqual(["note-2"])
  })

  test("notes_store_subscribe_receives_updates_and_unsubscribes", () => {
    // Arrange
    const listener = vi.fn()
    const unsubscribe = subscribeToNotes(listener)

    // Act
    upsertNote(createNote())

    // Assert
    expect(listener).toHaveBeenCalledWith(
      expect.arrayContaining([expect.objectContaining({ id: "note-1" })]),
    )

    // Act
    unsubscribe()
    upsertNote(createNote({ id: "note-2" }))

    // Assert
    expect(listener).toHaveBeenCalledTimes(1)
  })

  test("notes_store_updated_event_name_is_stable", () => {
    // Arrange / Act / Assert: components and tests depend on this contract.
    expect(NOTES_UPDATED_EVENT).toBe("kiizama-notes-updated")
  })
})
