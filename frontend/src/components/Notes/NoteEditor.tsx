import { Box, Flex, IconButton, Input, Text } from "@chakra-ui/react"
import { type KeyboardEvent, useEffect, useRef, useState } from "react"
import { useTranslation } from "react-i18next"
import { FiAlignLeft, FiCheckSquare, FiList, FiPlus } from "react-icons/fi"

import { Button } from "@/components/ui/button"
import { Checkbox } from "@/components/ui/checkbox"
import { formatDate } from "@/i18n"
import {
  MAX_NOTE_BLOCK_INDENT,
  type Note,
  type NoteBlock,
  type NoteBlockIndent,
  type NoteBlockType,
} from "@/lib/notes-store"
import { uuidv7 } from "@/lib/uuidv7"

const NOTE_TAG_PRESET_KEYS = [
  "work",
  "ideas",
  "meeting",
  "followUp",
  "personal",
  "urgent",
] as const

const NEXT_BLOCK_TYPE: Record<NoteBlockType, NoteBlockType> = {
  text: "bullet",
  bullet: "check",
  check: "text",
}

const BLOCK_TYPE_ICONS: Record<NoteBlockType, typeof FiAlignLeft> = {
  text: FiAlignLeft,
  bullet: FiList,
  check: FiCheckSquare,
}

export const NoteEditor = ({
  note,
  onChange,
}: {
  note: Note
  onChange: (note: Note) => void
}) => {
  const { i18n, t } = useTranslation("notes")
  const [customTagDraft, setCustomTagDraft] = useState("")
  const [focusBlockId, setFocusBlockId] = useState<string | null>(null)
  const blockInputRefs = useRef(new Map<string, HTMLInputElement>())

  useEffect(() => {
    if (!focusBlockId) {
      return
    }
    blockInputRefs.current.get(focusBlockId)?.focus()
    setFocusBlockId(null)
  }, [focusBlockId])

  const language = i18n.resolvedLanguage ?? i18n.language
  const createdAtLabel = t("note.createdAt", {
    date:
      formatDate(new Date(note.createdAt), language, {
        day: "2-digit",
        month: "long",
        year: "numeric",
      }) ?? note.createdAt,
  })

  const patchBlocks = (blocks: NoteBlock[]) => {
    onChange({ ...note, blocks })
  }

  const updateBlock = (blockId: string, patch: Partial<NoteBlock>) => {
    patchBlocks(
      note.blocks.map((block) =>
        block.id === blockId ? { ...block, ...patch } : block,
      ),
    )
  }

  const insertBlockAfter = (index: number) => {
    const currentBlock = note.blocks[index]
    const newBlock: NoteBlock = {
      id: uuidv7(),
      type: currentBlock.type,
      indent: currentBlock.indent,
      text: "",
      ...(currentBlock.type === "check" ? { checked: false } : {}),
    }
    const blocks = [...note.blocks]
    blocks.splice(index + 1, 0, newBlock)
    patchBlocks(blocks)
    setFocusBlockId(newBlock.id)
  }

  const removeBlockAt = (index: number) => {
    if (note.blocks.length <= 1) {
      return
    }
    const blocks = note.blocks.filter((_, blockIndex) => blockIndex !== index)
    patchBlocks(blocks)
    const focusTarget = blocks[Math.max(0, index - 1)]
    setFocusBlockId(focusTarget.id)
  }

  const appendBlock = () => {
    const newBlock: NoteBlock = {
      id: uuidv7(),
      type: "text",
      indent: 0,
      text: "",
    }
    patchBlocks([...note.blocks, newBlock])
    setFocusBlockId(newBlock.id)
  }

  const handleBlockKeyDown = (
    event: KeyboardEvent<HTMLInputElement>,
    block: NoteBlock,
    index: number,
  ) => {
    if (event.key === "Enter") {
      event.preventDefault()
      insertBlockAfter(index)
      return
    }

    if (event.key === "Tab") {
      event.preventDefault()
      const nextIndent = Math.min(
        MAX_NOTE_BLOCK_INDENT,
        Math.max(0, block.indent + (event.shiftKey ? -1 : 1)),
      ) as NoteBlockIndent
      if (nextIndent !== block.indent) {
        updateBlock(block.id, { indent: nextIndent })
      }
      return
    }

    if (event.key === "Backspace" && block.text === "") {
      if (note.blocks.length > 1) {
        event.preventDefault()
        removeBlockAt(index)
      }
    }
  }

  const cycleBlockType = (block: NoteBlock) => {
    const nextType = NEXT_BLOCK_TYPE[block.type]
    updateBlock(block.id, {
      type: nextType,
      checked: nextType === "check" ? (block.checked ?? false) : undefined,
    })
  }

  const applyCustomTag = () => {
    const tag = customTagDraft.trim()
    if (!tag) {
      return
    }
    onChange({ ...note, tag })
    setCustomTagDraft("")
  }

  return (
    <Box>
      <Input
        value={note.title}
        placeholder={t("note.titlePlaceholder")}
        variant="flushed"
        fontSize="2xl"
        fontWeight="black"
        letterSpacing="-0.02em"
        onChange={(event) => onChange({ ...note, title: event.target.value })}
      />
      <Text mt={2} color="ui.mutedText" fontSize="xs" fontWeight="bold">
        {createdAtLabel}
      </Text>

      <Flex mt={4} align="center" gap={2} wrap="wrap">
        <Text color="ui.mutedText" fontSize="xs" fontWeight="bold">
          {t("note.tagLabel")}
        </Text>
        <Button
          size="2xs"
          variant={note.tag === null ? "solid" : "outline"}
          onClick={() => onChange({ ...note, tag: null })}
        >
          {t("note.noTag")}
        </Button>
        {NOTE_TAG_PRESET_KEYS.map((presetKey) => {
          const presetTag = t(`note.tags.${presetKey}`)
          return (
            <Button
              key={presetKey}
              size="2xs"
              variant={note.tag === presetTag ? "solid" : "outline"}
              onClick={() => onChange({ ...note, tag: presetTag })}
            >
              {presetTag}
            </Button>
          )
        })}
        <Flex align="center" gap={1.5}>
          <Input
            value={customTagDraft}
            placeholder={t("note.customTagPlaceholder")}
            size="2xs"
            w="36"
            rounded="full"
            onChange={(event) => setCustomTagDraft(event.target.value)}
            onKeyDown={(event) => {
              if (event.key === "Enter") {
                event.preventDefault()
                applyCustomTag()
              }
            }}
          />
          <Button
            size="2xs"
            variant="outline"
            disabled={customTagDraft.trim() === ""}
            onClick={applyCustomTag}
          >
            {t("note.customTagApply")}
          </Button>
        </Flex>
        {note.tag !== null &&
        !NOTE_TAG_PRESET_KEYS.some(
          (presetKey) => t(`note.tags.${presetKey}`) === note.tag,
        ) ? (
          <Button size="2xs" variant="solid">
            {note.tag}
          </Button>
        ) : null}
      </Flex>

      <Flex mt={6} direction="column" gap={1.5}>
        {note.blocks.map((block, index) => {
          const TypeIcon = BLOCK_TYPE_ICONS[block.type]
          return (
            <Flex
              key={block.id}
              align="center"
              gap={2}
              ps={`${block.indent * 28}px`}
              data-indent={block.indent}
              data-testid="note-block"
            >
              <IconButton
                aria-label={t("note.lineTypeToggle")}
                size="2xs"
                variant="ghost"
                color="ui.mutedText"
                onClick={() => cycleBlockType(block)}
              >
                <TypeIcon />
              </IconButton>

              {block.type === "bullet" ? (
                <Text color="ui.secondaryText" fontWeight="black">
                  •
                </Text>
              ) : null}
              {block.type === "check" ? (
                <Checkbox
                  checked={block.checked ?? false}
                  inputProps={{ "aria-label": t("note.checkAria") }}
                  onCheckedChange={({ checked }) =>
                    updateBlock(block.id, { checked: checked === true })
                  }
                />
              ) : null}

              <Input
                ref={(element) => {
                  if (element) {
                    blockInputRefs.current.set(block.id, element)
                  } else {
                    blockInputRefs.current.delete(block.id)
                  }
                }}
                value={block.text}
                placeholder={t("note.blockPlaceholder")}
                variant="flushed"
                size="sm"
                color={
                  block.type === "check" && block.checked
                    ? "ui.mutedText"
                    : undefined
                }
                textDecoration={
                  block.type === "check" && block.checked
                    ? "line-through"
                    : undefined
                }
                onChange={(event) =>
                  updateBlock(block.id, { text: event.target.value })
                }
                onKeyDown={(event) => handleBlockKeyDown(event, block, index)}
              />
            </Flex>
          )
        })}
      </Flex>

      <Button mt={4} size="sm" variant="outline" onClick={appendBlock}>
        <FiPlus />
        {t("note.addLine")}
      </Button>
    </Box>
  )
}
