import {
  Button,
  DialogActionTrigger,
  DialogRoot,
  DialogTrigger,
  Flex,
  Input,
  NativeSelect,
  Text,
  VStack,
} from "@chakra-ui/react"
import { useMutation, useQueryClient } from "@tanstack/react-query"
import { useEffect, useState } from "react"
import { Controller, type SubmitHandler, useForm } from "react-hook-form"
import { FaExchangeAlt } from "react-icons/fa"

import {
  type AdminUserPublic,
  type AdminUserUpdate,
  UsersService,
} from "@/client"
import type { ApiError } from "@/client/core/ApiError"
import useCustomToast from "@/hooks/useCustomToast"
import {
  confirmPasswordRules,
  emailPattern,
  handleError,
  newPasswordRules,
} from "@/utils"
import { Checkbox } from "../ui/checkbox"
import {
  DialogBody,
  DialogCloseTrigger,
  DialogContent,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "../ui/dialog"
import { Field } from "../ui/field"

interface EditUserProps {
  user: AdminUserPublic
}

interface UserUpdateForm extends AdminUserUpdate {
  confirm_password?: string
}

const EditUser = ({ user }: EditUserProps) => {
  const [isOpen, setIsOpen] = useState(false)
  const queryClient = useQueryClient()
  const { showSuccessToast } = useCustomToast()
  const {
    control,
    register,
    handleSubmit,
    reset,
    getValues,
    setValue,
    watch,
    formState: { errors, isSubmitting },
  } = useForm<UserUpdateForm>({
    mode: "onBlur",
    criteriaMode: "all",
    defaultValues: user,
  })

  const mutation = useMutation({
    mutationFn: (data: UserUpdateForm) =>
      UsersService.updateUser({ userId: user.id, requestBody: data }),
    onSuccess: () => {
      showSuccessToast("User updated successfully.")
      reset()
      setIsOpen(false)
    },
    onError: (err: ApiError) => {
      handleError(err)
    },
    onSettled: () => {
      queryClient.invalidateQueries({ queryKey: ["users"] })
    },
  })

  const isSaving = isSubmitting || mutation.isPending
  const currentIsSuperuser = watch("is_superuser")
  const currentAccessProfile = watch("access_profile")
  const superuserTransitionLocked = user.access_profile === "ambassador"
  const ambassadorTransitionLocked =
    user.is_superuser || Boolean(currentIsSuperuser)

  useEffect(() => {
    if (ambassadorTransitionLocked && currentAccessProfile === "ambassador") {
      setValue("access_profile", "standard", { shouldDirty: true })
    }
  }, [ambassadorTransitionLocked, currentAccessProfile, setValue])

  useEffect(() => {
    if (superuserTransitionLocked && currentIsSuperuser) {
      setValue("is_superuser", false, { shouldDirty: true })
    }
  }, [currentIsSuperuser, setValue, superuserTransitionLocked])

  const onSubmit: SubmitHandler<UserUpdateForm> = async (data) => {
    const { confirm_password: _confirmPassword, ...rest } = data
    const payload: AdminUserUpdate = {
      ...rest,
      password: rest.password || undefined,
    }
    await mutation.mutateAsync(payload)
  }

  return (
    <DialogRoot
      size={{ base: "xs", md: "md" }}
      placement="center"
      open={isOpen}
      onOpenChange={({ open }) => setIsOpen(open)}
    >
      <DialogTrigger asChild>
        <Button variant="ghost" size="sm">
          <FaExchangeAlt fontSize="16px" />
          Edit User
        </Button>
      </DialogTrigger>
      <DialogContent>
        <form onSubmit={handleSubmit(onSubmit)}>
          <DialogHeader>
            <DialogTitle>Edit User</DialogTitle>
          </DialogHeader>
          <DialogBody>
            <Text mb={4}>Update the user details below.</Text>
            <VStack gap={4}>
              <Field
                required
                invalid={!!errors.email}
                errorText={errors.email?.message}
                label="Email"
              >
                <Input
                  {...register("email", {
                    required: "Email is required",
                    pattern: emailPattern,
                  })}
                  placeholder="Email"
                  type="email"
                />
              </Field>

              <Field
                invalid={!!errors.full_name}
                errorText={errors.full_name?.message}
                label="Full Name"
              >
                <Input
                  {...register("full_name")}
                  placeholder="Full name"
                  type="text"
                />
              </Field>

              <Field
                invalid={!!errors.password}
                errorText={errors.password?.message}
                label="Set Password"
              >
                <Input
                  {...register("password", newPasswordRules(false))}
                  placeholder="Password"
                  type="password"
                />
              </Field>

              <Field
                invalid={!!errors.confirm_password}
                errorText={errors.confirm_password?.message}
                label="Confirm Password"
              >
                <Input
                  {...register(
                    "confirm_password",
                    confirmPasswordRules(getValues, false),
                  )}
                  placeholder="Password"
                  type="password"
                />
              </Field>

              <Controller
                control={control}
                name="access_profile"
                render={({ field }) => (
                  <Field label="Access Profile">
                    <NativeSelect.Root>
                      <NativeSelect.Field
                        value={field.value ?? "standard"}
                        onChange={(event) => field.onChange(event.target.value)}
                      >
                        <option value="standard">Standard</option>
                        <option
                          value="ambassador"
                          disabled={ambassadorTransitionLocked}
                        >
                          Ambassador
                        </option>
                      </NativeSelect.Field>
                      <NativeSelect.Indicator />
                    </NativeSelect.Root>
                  </Field>
                )}
              />
              <Text fontSize="sm" color="ui.secondaryText" alignSelf="stretch">
                {user.is_superuser || user.access_profile === "ambassador"
                  ? "Move the user to Standard and save before switching to Superuser or Ambassador."
                  : "Superusers and ambassadors are mutually exclusive. Move the user to Standard first before switching between them."}
              </Text>
            </VStack>

            <Flex mt={4} direction="column" gap={4}>
              <Controller
                control={control}
                name="is_superuser"
                render={({ field }) => (
                  <Field disabled={field.disabled} colorPalette="design">
                    <Checkbox
                      checked={field.value ?? false}
                      onCheckedChange={({ checked }) => field.onChange(checked)}
                      disabled={superuserTransitionLocked}
                    >
                      Is superuser?
                    </Checkbox>
                  </Field>
                )}
              />
              <Controller
                control={control}
                name="is_active"
                render={({ field }) => (
                  <Field disabled={field.disabled} colorPalette="design">
                    <Checkbox
                      checked={field.value ?? false}
                      onCheckedChange={({ checked }) => field.onChange(checked)}
                    >
                      Is active?
                    </Checkbox>
                  </Field>
                )}
              />
            </Flex>
          </DialogBody>

          <DialogFooter gap={2}>
            <DialogActionTrigger asChild>
              <Button variant="subtle" colorPalette="gray" disabled={isSaving}>
                Cancel
              </Button>
            </DialogActionTrigger>
            <Button
              variant="solid"
              type="submit"
              loading={isSaving}
              disabled={isSaving}
            >
              Save
            </Button>
          </DialogFooter>
          <DialogCloseTrigger />
        </form>
      </DialogContent>
    </DialogRoot>
  )
}

export default EditUser
