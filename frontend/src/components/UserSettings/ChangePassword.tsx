import { Box, Button, Container, Heading, VStack } from "@chakra-ui/react"
import { useMutation } from "@tanstack/react-query"
import { type SubmitHandler, useForm } from "react-hook-form"
import { FiLock } from "react-icons/fi"

import { type ApiError, type UpdatePassword, UsersService } from "@/client"
import useCustomToast from "@/hooks/useCustomToast"
import {
  confirmPasswordRules,
  handleError,
  newPasswordRules,
  passwordRules,
} from "@/utils"
import { PasswordInput } from "../ui/password-input"
import { PasswordRequirements } from "../ui/password-requirements"

interface UpdatePasswordForm extends UpdatePassword {
  confirm_password: string
}

const ChangePassword = () => {
  const { showSuccessToast } = useCustomToast()
  const {
    register,
    handleSubmit,
    reset,
    getValues,
    watch,
    formState: { errors, isSubmitting },
  } = useForm<UpdatePasswordForm>({
    mode: "onBlur",
    criteriaMode: "all",
  })

  const mutation = useMutation({
    mutationFn: (data: UpdatePassword) =>
      UsersService.updatePasswordMe({ requestBody: data }),
    onSuccess: () => {
      showSuccessToast("Password updated successfully.")
      reset()
    },
    onError: (err: ApiError) => {
      handleError(err)
    },
  })
  const newPasswordValue = watch("new_password")

  const onSubmit: SubmitHandler<UpdatePasswordForm> = async (data) => {
    mutation.mutate(data)
  }

  return (
    <Container maxW="full">
      <Heading size="sm" py={4}>
        Change Password
      </Heading>
      <Box as="form" onSubmit={handleSubmit(onSubmit)}>
        <VStack gap={4} w={{ base: "100%", md: "sm" }}>
          <PasswordInput
            type="current_password"
            startElement={<FiLock />}
            {...register("current_password", passwordRules())}
            placeholder="Current Password"
            errors={errors}
          />
          <PasswordInput
            type="new_password"
            startElement={<FiLock />}
            {...register("new_password", newPasswordRules())}
            placeholder="New Password"
            errors={errors}
            helperText={<PasswordRequirements password={newPasswordValue} />}
          />
          <PasswordInput
            type="confirm_password"
            startElement={<FiLock />}
            {...register("confirm_password", confirmPasswordRules(getValues))}
            placeholder="Confirm Password"
            errors={errors}
          />
        </VStack>
        <Button
          layerStyle="brandGradientButton"
          mt={4}
          type="submit"
          loading={isSubmitting}
        >
          Save
        </Button>
      </Box>
    </Container>
  )
}
export default ChangePassword
