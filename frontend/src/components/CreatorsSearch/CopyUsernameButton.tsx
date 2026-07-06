import { Clipboard, IconButton } from "@chakra-ui/react"
import { useTranslation } from "react-i18next"
import { FaRegCopy } from "react-icons/fa"
import { FiCheck } from "react-icons/fi"

export const CopyUsernameButton = ({ username }: { username: string }) => {
  const { t } = useTranslation("common")

  return (
    <Clipboard.Root value={username} display="inline-flex" flexShrink={0}>
      <Clipboard.Trigger asChild>
        <IconButton
          aria-label={t("actions.copyUsername")}
          size="2xs"
          variant="ghost"
          color="ui.mutedText"
          _hover={{ color: "ui.text", bg: "ui.surfaceSoft" }}
        >
          <Clipboard.Indicator copied={<FiCheck />}>
            <FaRegCopy />
          </Clipboard.Indicator>
        </IconButton>
      </Clipboard.Trigger>
    </Clipboard.Root>
  )
}
