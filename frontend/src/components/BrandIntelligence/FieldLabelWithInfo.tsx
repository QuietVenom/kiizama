import { IconButton, Portal, Text, Tooltip } from "@chakra-ui/react"
import { memo } from "react"
import { useTranslation } from "react-i18next"
import { FiInfo } from "react-icons/fi"

type FieldLabelWithInfoProps = {
  description: string
  label: string
}

const tooltipPositioning = { placement: "top" } as const
const tooltipHoverStyles = { bg: "ui.surfaceSoft", color: "ui.text" } as const

const FieldLabelWithInfo = memo(
  ({ description, label }: FieldLabelWithInfoProps) => {
    const { t } = useTranslation("brandIntelligence")

    if (!description) return null

    return (
      <Tooltip.Root
        openDelay={160}
        lazyMount
        unmountOnExit
        skipAnimationOnMount
        positioning={tooltipPositioning}
      >
        <Tooltip.Trigger asChild>
          <IconButton
            aria-label={t("tooltips.helpButton", { label })}
            variant="ghost"
            size="sm"
            type="button"
            color="ui.mutedText"
            _hover={tooltipHoverStyles}
          >
            <FiInfo />
          </IconButton>
        </Tooltip.Trigger>
        <Portal>
          <Tooltip.Positioner>
            <Tooltip.Content
              maxW="320px"
              rounded="2xl"
              borderWidth="1px"
              borderColor="ui.border"
              bg="ui.panel"
              px={4}
              py={3}
              color="ui.text"
              boxShadow="lg"
            >
              <Tooltip.Arrow>
                <Tooltip.ArrowTip />
              </Tooltip.Arrow>
              <Text fontSize="sm" lineHeight="1.7">
                {description}
              </Text>
            </Tooltip.Content>
          </Tooltip.Positioner>
        </Portal>
      </Tooltip.Root>
    )
  },
)

FieldLabelWithInfo.displayName = "FieldLabelWithInfo"

export default FieldLabelWithInfo
