import type { ApiError } from "./client"
import useCustomToast from "./hooks/useCustomToast"

export const emailPattern = {
  value: /^[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}$/i,
  message: "Invalid email address",
}

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

export const passwordRules = (isRequired = true) => {
  const rules: any = {
    minLength: {
      value: PASSWORD_MIN_LENGTH,
      message: `Password must be at least ${PASSWORD_MIN_LENGTH} characters`,
    },
  }

  if (isRequired) {
    rules.required = "Password is required"
  }

  return rules
}

const getNewPasswordError = (value: string) => {
  if (
    value.length < PASSWORD_MIN_LENGTH ||
    value.length > PASSWORD_MAX_LENGTH
  ) {
    return `Password must be between ${PASSWORD_MIN_LENGTH} and ${PASSWORD_MAX_LENGTH} characters`
  }
  if (!passwordHasUppercase(value)) {
    return "Password must include at least 1 uppercase letter"
  }
  if (!passwordHasNumber(value)) {
    return "Password must include at least 1 number"
  }
  if (!passwordHasAllowedSpecialCharacter(value)) {
    return `Password must include at least 1 special character (${PASSWORD_SPECIAL_CHARACTERS.join(", ")})`
  }
  return true
}

export const newPasswordRules = (isRequired = true) => {
  const rules: any = {
    validate: (value: string) => {
      if (!value && !isRequired) {
        return true
      }
      return getNewPasswordError(value)
    },
  }

  if (isRequired) {
    rules.required = "Password is required"
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

export const getPasswordRequirementStates = (
  password: string,
): PasswordRequirementState[] => {
  const value = password ?? ""

  return [
    {
      key: "length",
      label: `${PASSWORD_MIN_LENGTH}-${PASSWORD_MAX_LENGTH} characters`,
      satisfied:
        value.length >= PASSWORD_MIN_LENGTH &&
        value.length <= PASSWORD_MAX_LENGTH,
    },
    {
      key: "uppercase",
      label: "At least 1 uppercase letter",
      satisfied: passwordHasUppercase(value),
    },
    {
      key: "number",
      label: "At least 1 number",
      satisfied: passwordHasNumber(value),
    },
    {
      key: "special",
      label: `At least 1 special character (${PASSWORD_SPECIAL_CHARACTERS.join(" ")})`,
      satisfied: passwordHasAllowedSpecialCharacter(value),
    },
  ]
}

export const confirmPasswordRules = (
  getValues: () => any,
  isRequired = true,
) => {
  const rules: any = {
    validate: (value: string) => {
      const password = getValues().password || getValues().new_password
      return value === password ? true : "The passwords do not match"
    },
  }

  if (isRequired) {
    rules.required = "Password confirmation is required"
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
