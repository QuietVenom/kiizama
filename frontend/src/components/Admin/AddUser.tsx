import {
  Button,
  DialogActionTrigger,
  DialogTitle,
  Flex,
  Input,
  NativeSelect,
  Text,
  VStack,
} from "@chakra-ui/react"
import { useMutation, useQueryClient } from "@tanstack/react-query"
import { useEffect, useState } from "react"
import { Controller, type SubmitHandler, useForm } from "react-hook-form"
import { FaPlus } from "react-icons/fa"
import { type AdminUserCreate, UsersService } from "@/client"
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
  DialogRoot,
  DialogTrigger,
} from "../ui/dialog"
import { Field } from "../ui/field"

interface UserCreateForm extends AdminUserCreate {
  confirm_password: string
}

const AddUser = () => {
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
    formState: { errors, isValid, isSubmitting },
  } = useForm<UserCreateForm>({
    mode: "onBlur",
    criteriaMode: "all",
    defaultValues: {
      email: "",
      full_name: "",
      password: "",
      confirm_password: "",
      access_profile: "standard",
      is_superuser: false,
      is_active: false,
    },
  })

  const mutation = useMutation({
    mutationFn: (data: AdminUserCreate) =>
      UsersService.createUser({ requestBody: data }),
    onSuccess: () => {
      showSuccessToast("User created successfully.")
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

  useEffect(() => {
    if (currentIsSuperuser && currentAccessProfile === "ambassador") {
      setValue("access_profile", "standard", { shouldDirty: true })
    }
  }, [currentAccessProfile, currentIsSuperuser, setValue])

  const onSubmit: SubmitHandler<UserCreateForm> = async (data) => {
    try {
      await mutation.mutateAsync(data)
    } catch {
      // onError owns user-facing error handling; avoid leaking rejected submits.
    }
  }

  return (
    <DialogRoot
      size={{ base: "xs", md: "md" }}
      placement="center"
      open={isOpen}
      onOpenChange={({ open }) => setIsOpen(open)}
    >
      <DialogTrigger asChild>
        <Button value="add-user" my={4} layerStyle="brandGradientButton">
          <FaPlus fontSize="16px" />
          Add User
        </Button>
      </DialogTrigger>
      <DialogContent>
        <form onSubmit={handleSubmit(onSubmit)}>
          <DialogHeader>
            <DialogTitle>Add User</DialogTitle>
          </DialogHeader>
          <DialogBody>
            <Text mb={4}>
              Fill in the form below to add a new user to the system.
            </Text>
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
                required
                invalid={!!errors.password}
                errorText={errors.password?.message}
                label="Set Password"
              >
                <Input
                  {...register("password", newPasswordRules())}
                  placeholder="Password"
                  type="password"
                />
              </Field>

              <Field
                required
                invalid={!!errors.confirm_password}
                errorText={errors.confirm_password?.message}
                label="Confirm Password"
              >
                <Input
                  {...register(
                    "confirm_password",
                    confirmPasswordRules(getValues),
                  )}
                  placeholder="Password"
                  type="password"
                />
              </Field>

              <Controller
                control={control}
                name="access_profile"
                render={({ field }) => (
                  <Field
                    required
                    invalid={!!errors.access_profile}
                    errorText={errors.access_profile?.message}
                    label="Access Profile"
                  >
                    <NativeSelect.Root>
                      <NativeSelect.Field
                        value={field.value}
                        onChange={(event) => field.onChange(event.target.value)}
                      >
                        <option value="standard">Standard</option>
                        <option
                          value="ambassador"
                          disabled={Boolean(currentIsSuperuser)}
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
                {currentIsSuperuser
                  ? "Superusers can only be created as Standard users. Move them to Standard first before changing to Ambassador later."
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
                      checked={field.value}
                      onCheckedChange={({ checked }) => field.onChange(checked)}
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
                      checked={field.value}
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
              layerStyle="brandGradientButton"
              type="submit"
              disabled={!isValid || isSaving}
              loading={isSaving}
            >
              Save
            </Button>
          </DialogFooter>
        </form>
        <DialogCloseTrigger />
      </DialogContent>
    </DialogRoot>
  )
}

export default AddUser
