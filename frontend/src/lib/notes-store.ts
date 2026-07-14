export const NOTES_STORAGE_KEY = "kiizama-notes"
export const NOTES_UPDATED_EVENT = "kiizama-notes-updated"

export type NoteBlockType = "text" | "bullet" | "check"
export type NoteBlockIndent = 0 | 1 | 2

export const MAX_NOTE_BLOCK_INDENT: NoteBlockIndent = 2

export type NoteBlock = {
  id: string
  type: NoteBlockType
  indent: NoteBlockIndent
  text: string
  checked?: boolean
}

export type Note = {
  id: string
  title: string
  tag: string | null
  createdAt: string
  updatedAt: string
  blocks: NoteBlock[]
}

type NotesUpdatedDetail = {
  notes: Note[]
}

const isRecord = (value: unknown): value is Record<string, unknown> =>
  typeof value === "object" && value !== null && !Array.isArray(value)

const isNoteBlock = (value: unknown): value is NoteBlock => {
  if (!isRecord(value)) {
    return false
  }

  return (
    typeof value.id === "string" &&
    (value.type === "text" ||
      value.type === "bullet" ||
      value.type === "check") &&
    (value.indent === 0 || value.indent === 1 || value.indent === 2) &&
    typeof value.text === "string" &&
    (value.checked === undefined || typeof value.checked === "boolean")
  )
}

const isNote = (value: unknown): value is Note => {
  if (!isRecord(value)) {
    return false
  }

  return (
    typeof value.id === "string" &&
    typeof value.title === "string" &&
    (typeof value.tag === "string" || value.tag === null) &&
    typeof value.createdAt === "string" &&
    typeof value.updatedAt === "string" &&
    Array.isArray(value.blocks) &&
    value.blocks.every(isNoteBlock)
  )
}

const dispatchNotesUpdated = (notes: Note[]) => {
  if (typeof window === "undefined") {
    return
  }

  window.dispatchEvent(
    new CustomEvent<NotesUpdatedDetail>(NOTES_UPDATED_EVENT, {
      detail: { notes },
    }),
  )
}

const persistNotes = (notes: Note[]) => {
  if (typeof window === "undefined") {
    return notes
  }

  localStorage.setItem(NOTES_STORAGE_KEY, JSON.stringify(notes))
  dispatchNotesUpdated(notes)
  return notes
}

export const readNotes = (): Note[] => {
  if (typeof window === "undefined") {
    return []
  }

  try {
    const rawValue = localStorage.getItem(NOTES_STORAGE_KEY)
    if (!rawValue) {
      return []
    }

    const parsed: unknown = JSON.parse(rawValue)
    if (!Array.isArray(parsed)) {
      return []
    }

    return parsed.filter(isNote)
  } catch {
    return []
  }
}

export const upsertNote = (note: Note) => {
  const currentNotes = readNotes()
  const nextNotes = currentNotes.filter(
    (currentNote) => currentNote.id !== note.id,
  )
  nextNotes.unshift(note)
  return persistNotes(nextNotes)
}

export const removeNote = (noteId: string) => {
  const nextNotes = readNotes().filter((note) => note.id !== noteId)
  return persistNotes(nextNotes)
}

export const subscribeToNotes = (listener: (notes: Note[]) => void) => {
  if (typeof window === "undefined") {
    return () => {}
  }

  const handleUpdated = (event: Event) => {
    const detail = (event as CustomEvent<NotesUpdatedDetail>).detail
    listener(detail?.notes ?? readNotes())
  }

  const handleStorage = (event: StorageEvent) => {
    if (event.key === NOTES_STORAGE_KEY) {
      listener(readNotes())
    }
  }

  window.addEventListener(NOTES_UPDATED_EVENT, handleUpdated)
  window.addEventListener("storage", handleStorage)

  return () => {
    window.removeEventListener(NOTES_UPDATED_EVENT, handleUpdated)
    window.removeEventListener("storage", handleStorage)
  }
}
