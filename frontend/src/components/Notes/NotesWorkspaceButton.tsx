import { IconButton } from "@chakra-ui/react"
import { useState } from "react"
import { useTranslation } from "react-i18next"
import { LuNotebookPen } from "react-icons/lu"

import { NotesWorkspaceDialog } from "./NotesWorkspaceDialog"

export const NotesWorkspaceButton = () => {
  const { t } = useTranslation("notes")
  const [isOpen, setIsOpen] = useState(false)

  return (
    <>
      <IconButton
        aria-label={t("topbar.button")}
        variant="outline"
        rounded="2xl"
        onClick={() => setIsOpen(true)}
      >
        <LuNotebookPen />
      </IconButton>

      <NotesWorkspaceDialog open={isOpen} onOpenChange={setIsOpen} />
    </>
  )
}
