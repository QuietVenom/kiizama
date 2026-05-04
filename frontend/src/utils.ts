import type { ApiError } from "./client"
import useCustomToast from "./hooks/useCustomToast"

export const emailPattern = {
  value: /^[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}$/i,
  message: "Invalid email address",
}

export const buildEmailPattern = (message = emailPattern.message) => ({
  value: emailPattern.value,
  message,
})

export const namePattern = {
  value: /^[A-Za-z\s\u00C0-\u017F]{1,30}$/,
  message: "Invalid name",
}

export const PASSWORD_MIN_LENGTH = 8
export const PASSWORD_MAX_LENGTH = 25
export const PASSWORD_SPECIAL_CHARACTERS = ["!", "@", "#", "$", "%"] as const

const passwordHasUppercase = (value: string) => /[A-Z]/.test(value)
const passwordHasNumber = (value: string) => /\d/.test(value)
const passwordHasAllowedSpecialCharacter = (value: string) =>
  PASSWORD_SPECIAL_CHARACTERS.some((character) => value.includes(character))

type PasswordRulesMessages = {
  minLength: string
  required: string
}

export const passwordRules = (
  isRequired = true,
  messages?: Partial<PasswordRulesMessages>,
) => {
  const resolvedMessages: PasswordRulesMessages = {
    minLength:
      messages?.minLength ??
      `Password must be at least ${PASSWORD_MIN_LENGTH} characters`,
    required: messages?.required ?? "Password is required",
  }
  const rules: any = {
    minLength: {
      value: PASSWORD_MIN_LENGTH,
      message: resolvedMessages.minLength,
    },
  }

  if (isRequired) {
    rules.required = resolvedMessages.required
  }

  return rules
}

type NewPasswordMessages = {
  required: string
  length: string
  uppercase: string
  number: string
  special: string
}

const getDefaultNewPasswordMessages = (): NewPasswordMessages => ({
  required: "Password is required",
  length: `Password must be between ${PASSWORD_MIN_LENGTH} and ${PASSWORD_MAX_LENGTH} characters`,
  uppercase: "Password must include at least 1 uppercase letter",
  number: "Password must include at least 1 number",
  special: `Password must include at least 1 special character (${PASSWORD_SPECIAL_CHARACTERS.join(", ")})`,
})

const getNewPasswordError = (
  value: string,
  messages: NewPasswordMessages = getDefaultNewPasswordMessages(),
) => {
  if (
    value.length < PASSWORD_MIN_LENGTH ||
    value.length > PASSWORD_MAX_LENGTH
  ) {
    return messages.length
  }
  if (!passwordHasUppercase(value)) {
    return messages.uppercase
  }
  if (!passwordHasNumber(value)) {
    return messages.number
  }
  if (!passwordHasAllowedSpecialCharacter(value)) {
    return messages.special
  }
  return true
}

export const newPasswordRules = (
  isRequired = true,
  messages?: Partial<NewPasswordMessages>,
) => {
  const resolvedMessages: NewPasswordMessages = {
    ...getDefaultNewPasswordMessages(),
    ...messages,
  }
  const rules: any = {
    validate: (value: string) => {
      if (!value && !isRequired) {
        return true
      }
      return getNewPasswordError(value, resolvedMessages)
    },
  }

  if (isRequired) {
    rules.required = resolvedMessages.required
  }

  return rules
}

export type PasswordRequirementKey =
  | "length"
  | "uppercase"
  | "number"
  | "special"

export interface PasswordRequirementState {
  key: PasswordRequirementKey
  label: string
  satisfied: boolean
}

type PasswordRequirementLabels = {
  length: string
  uppercase: string
  number: string
  special: string
}

export const getPasswordRequirementStates = (
  password: string,
  labels?: Partial<PasswordRequirementLabels>,
): PasswordRequirementState[] => {
  const value = password ?? ""
  const resolvedLabels: PasswordRequirementLabels = {
    length: `${PASSWORD_MIN_LENGTH}-${PASSWORD_MAX_LENGTH} characters`,
    uppercase: "At least 1 uppercase letter",
    number: "At least 1 number",
    special: `At least 1 special character (${PASSWORD_SPECIAL_CHARACTERS.join(" ")})`,
    ...labels,
  }

  return [
    {
      key: "length",
      label: resolvedLabels.length,
      satisfied:
        value.length >= PASSWORD_MIN_LENGTH &&
        value.length <= PASSWORD_MAX_LENGTH,
    },
    {
      key: "uppercase",
      label: resolvedLabels.uppercase,
      satisfied: passwordHasUppercase(value),
    },
    {
      key: "number",
      label: resolvedLabels.number,
      satisfied: passwordHasNumber(value),
    },
    {
      key: "special",
      label: resolvedLabels.special,
      satisfied: passwordHasAllowedSpecialCharacter(value),
    },
  ]
}

type ConfirmPasswordMessages = {
  mismatch: string
  required: string
}

export const confirmPasswordRules = (
  getValues: () => any,
  isRequired = true,
  messages?: Partial<ConfirmPasswordMessages>,
) => {
  const resolvedMessages: ConfirmPasswordMessages = {
    mismatch: "The passwords do not match",
    required: "Password confirmation is required",
    ...messages,
  }
  const rules: any = {
    validate: (value: string) => {
      const password = getValues().password || getValues().new_password
      if (!isRequired && !password && !value) {
        return true
      }
      return value === password ? true : resolvedMessages.mismatch
    },
  }

  if (isRequired) {
    rules.required = resolvedMessages.required
  }

  return rules
}

export const handleError = (err: ApiError) => {
  const { showErrorToast } = useCustomToast()
  const errDetail = (err.body as any)?.detail
  let errorMessage = errDetail || "Something went wrong."
  if (Array.isArray(errDetail) && errDetail.length > 0) {
    errorMessage = errDetail[0].msg
  }
  showErrorToast(errorMessage)
}
