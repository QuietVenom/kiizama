import { TagsInputField } from "@/components/ui/tags-input-field"

const MAX_USERNAMES = 50

type UsernameTagsInputProps = {
  disabled?: boolean
  expiredValues?: ReadonlySet<string>
  invalid?: boolean
  invalidValues?: ReadonlySet<string>
  missingValues?: ReadonlySet<string>
  onMaxExceeded?: () => void
  onValueChange: (value: string[]) => void
  placeholder?: string
  value: string[]
}

const getTagPalette = (
  username: string,
  expiredValues: ReadonlySet<string>,
  invalidValues: ReadonlySet<string>,
  missingValues: ReadonlySet<string>,
) => {
  if (invalidValues.has(username) || missingValues.has(username)) {
    return {
      background: "ui.dangerSoft",
      borderColor: "ui.danger",
      color: "ui.dangerText",
      closeHoverBg: "rgba(220, 38, 38, 0.12)",
    }
  }

  if (expiredValues.has(username)) {
    return {
      background: "ui.warningSoft",
      borderColor: "ui.warning",
      color: "ui.warningText",
      closeHoverBg: "rgba(217, 119, 6, 0.12)",
    }
  }

  return {
    background: "ui.brandSoft",
    borderColor: "ui.brandBorderSoft",
    color: "ui.brandText",
    closeHoverBg: "rgba(249, 115, 22, 0.10)",
  }
}

const UsernameTagsInput = ({
  disabled,
  expiredValues = new Set<string>(),
  invalid,
  invalidValues = new Set<string>(),
  missingValues = new Set<string>(),
  onMaxExceeded,
  onValueChange,
  placeholder = "Add usernames and press Enter",
  value,
}: UsernameTagsInputProps) => {
  return (
    <TagsInputField
      disabled={disabled}
      getTagPalette={(username) =>
        getTagPalette(username, expiredValues, invalidValues, missingValues)
      }
      invalid={invalid}
      max={MAX_USERNAMES}
      onMaxExceeded={onMaxExceeded}
      onValueChange={onValueChange}
      placeholder={placeholder}
      renderTagLabel={(username) => `@${username}`}
      value={value}
    />
  )
}

export default UsernameTagsInput
