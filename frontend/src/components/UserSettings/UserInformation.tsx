import {
  Box,
  Button,
  Container,
  Flex,
  Heading,
  Input,
  Text,
} from "@chakra-ui/react"
import { useMutation, useQueryClient } from "@tanstack/react-query"
import { useState } from "react"
import { type SubmitHandler, useForm } from "react-hook-form"
import { useTranslation } from "react-i18next"

import {
  type ApiError,
  type UserPublic,
  UsersService,
  type UserUpdateMe,
} from "@/client"
import useAuth, { currentUserQueryOptions } from "@/hooks/useAuth"
import useCustomToast from "@/hooks/useCustomToast"
import { buildEmailPattern, handleError } from "@/utils"
import { Field } from "../ui/field"

const UserInformation = () => {
  const { t } = useTranslation("settings")
  const fullNameFieldId = "user-full-name"
  const emailFieldId = "user-email"
  const queryClient = useQueryClient()
  const { showSuccessToast } = useCustomToast()
  const [editMode, setEditMode] = useState(false)
  const { user: currentUser } = useAuth()
  const {
    register,
    handleSubmit,
    reset,
    getValues,
    formState: { isSubmitting, errors, isDirty },
  } = useForm<UserPublic>({
    mode: "onBlur",
    criteriaMode: "all",
    defaultValues: {
      full_name: currentUser?.full_name,
      email: currentUser?.email,
    },
  })

  const openEditMode = () => {
    setEditMode(true)
  }

  const mutation = useMutation({
    mutationFn: (data: UserUpdateMe) =>
      UsersService.updateUserMe({ requestBody: data }),
    onSuccess: (updatedUser) => {
      queryClient.setQueryData(currentUserQueryOptions.queryKey, updatedUser)
      reset(updatedUser)
      setEditMode(false)
      showSuccessToast(t("userInformation.successToast"))
    },
    onError: (err: ApiError) => {
      handleError(err)
    },
    onSettled: () => {
      queryClient.invalidateQueries()
    },
  })

  const onSubmit: SubmitHandler<UserUpdateMe> = async (data) => {
    mutation.mutate(data)
  }

  const onCancel = () => {
    reset()
    setEditMode(false)
  }

  return (
    <Container maxW="full">
      <Heading size="sm" py={4}>
        {t("userInformation.title")}
      </Heading>
      <Box
        w={{ sm: "full", md: "sm" }}
        as="form"
        onSubmit={handleSubmit(onSubmit)}
      >
        <Field
          label={t("userInformation.fullNameLabel")}
          labelMode={editMode ? "label" : "text"}
          ids={editMode ? { control: fullNameFieldId } : undefined}
        >
          {editMode ? (
            <Input
              id={fullNameFieldId}
              aria-label={t("userInformation.fullNameLabel")}
              {...register("full_name", { maxLength: 30 })}
              type="text"
              size="md"
            />
          ) : (
            <Text
              fontSize="md"
              py={2}
              color={!currentUser?.full_name ? "gray" : "inherit"}
              truncate
              maxW="sm"
            >
              {currentUser?.full_name || t("userInformation.notAvailable")}
            </Text>
          )}
        </Field>
        <Field
          mt={4}
          label={t("userInformation.emailLabel")}
          labelMode={editMode ? "label" : "text"}
          ids={editMode ? { control: emailFieldId } : undefined}
          invalid={!!errors.email}
          errorText={errors.email?.message}
        >
          {editMode ? (
            <Input
              id={emailFieldId}
              aria-label={t("userInformation.emailLabel")}
              {...register("email", {
                required: t("userInformation.validation.emailRequired"),
                pattern: buildEmailPattern(
                  t("userInformation.validation.invalidEmail"),
                ),
              })}
              type="email"
              size="md"
            />
          ) : (
            <Text fontSize="md" py={2} truncate maxW="sm">
              {currentUser?.email}
            </Text>
          )}
        </Field>
        <Flex mt={4} gap={3}>
          <Button
            layerStyle="brandGradientButton"
            onClick={editMode ? undefined : openEditMode}
            type={editMode ? "submit" : "button"}
            loading={editMode ? isSubmitting : false}
            disabled={editMode ? !isDirty || !getValues("email") : false}
          >
            {editMode
              ? t("userInformation.actions.save")
              : t("userInformation.actions.edit")}
          </Button>
          {editMode && (
            <Button
              variant="subtle"
              colorPalette="gray"
              onClick={onCancel}
              disabled={isSubmitting}
            >
              {t("userInformation.actions.cancel")}
            </Button>
          )}
        </Flex>
      </Box>
    </Container>
  )
}

export default UserInformation
