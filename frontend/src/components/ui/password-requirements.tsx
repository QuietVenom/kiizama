import { HStack, Icon, Text, VStack } from "@chakra-ui/react"
import { useTranslation } from "react-i18next"
import { FiCheckCircle, FiCircle } from "react-icons/fi"

import { getPasswordRequirementStates } from "@/utils"

interface PasswordRequirementsProps {
  password?: string
}

export const PasswordRequirements = ({
  password = "",
}: PasswordRequirementsProps) => {
  const { t } = useTranslation("auth")
  const requirements = getPasswordRequirementStates(password, {
    length: t("password.requirements.items.length"),
    uppercase: t("password.requirements.items.uppercase"),
    number: t("password.requirements.items.number"),
    special: t("password.requirements.items.special"),
  })

  return (
    <VStack align="stretch" gap={1.5} pt={2}>
      <Text fontSize="xs" color="gray.500" fontWeight="medium">
        {t("password.requirements.title")}
      </Text>
      {requirements.map(({ key, label, satisfied }) => (
        <HStack
          key={key}
          gap={2}
          align="start"
          data-testid={`password-requirement-${key}`}
          data-satisfied={satisfied ? "true" : "false"}
        >
          <Icon
            as={satisfied ? FiCheckCircle : FiCircle}
            boxSize={4}
            mt="0.5"
            color={satisfied ? "green.500" : "gray.400"}
          />
          <Text fontSize="sm" color={satisfied ? "green.600" : "gray.500"}>
            {label}
          </Text>
        </HStack>
      ))}
    </VStack>
  )
}
