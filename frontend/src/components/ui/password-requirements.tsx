import { HStack, Icon, Text, VStack } from "@chakra-ui/react"
import { FiCheckCircle, FiCircle } from "react-icons/fi"

import { getPasswordRequirementStates } from "@/utils"

interface PasswordRequirementsProps {
  password?: string
}

export const PasswordRequirements = ({
  password = "",
}: PasswordRequirementsProps) => {
  const requirements = getPasswordRequirementStates(password)

  return (
    <VStack align="stretch" gap={1.5} pt={2}>
      <Text fontSize="xs" color="gray.500" fontWeight="medium">
        Password requirements
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
