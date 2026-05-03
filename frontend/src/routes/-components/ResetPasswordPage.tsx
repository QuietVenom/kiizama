import {
  Box,
  Link as ChakraLink,
  Container,
  Heading,
  IconButton,
  Image,
  Text,
} from "@chakra-ui/react"
import { useMutation } from "@tanstack/react-query"
import { useNavigate } from "@tanstack/react-router"
import { type SubmitHandler, useForm } from "react-hook-form"
import { useTranslation } from "react-i18next"
import { FiLock } from "react-icons/fi"

import { type ApiError, LoginService, type NewPassword } from "@/client"
import InsightCard from "@/components/Common/InsightCard"
import ThemeLogo from "@/components/Common/ThemeLogo"
import { Button } from "@/components/ui/button"
import { PasswordInput } from "@/components/ui/password-input"
import { PasswordRequirements } from "@/components/ui/password-requirements"
import useCustomToast from "@/hooks/useCustomToast"
import { confirmPasswordRules, handleError, newPasswordRules } from "@/utils"
import SymbolLogo from "/assets/images/symbol.svg"

interface NewPasswordForm extends NewPassword {
  confirm_password: string
}

const FORM_CONTAINER_MAX_W = { base: "md", md: "3xl" } as const
const FORM_CARD_MIN_H = { base: "auto", md: "560px" } as const
const FORM_CONTROL_MAX_W = { base: "full", md: "50%" } as const

export function ResetPasswordPage() {
  const { t } = useTranslation("auth")
  const landingUrl = "/"
  const {
    register,
    handleSubmit,
    getValues,
    reset,
    watch,
    formState: { errors },
  } = useForm<NewPasswordForm>({
    mode: "onBlur",
    criteriaMode: "all",
    defaultValues: {
      new_password: "",
    },
  })
  const { showSuccessToast } = useCustomToast()
  const navigate = useNavigate()
  const newPasswordValue = watch("new_password")

  const resetPassword = async (data: NewPassword) => {
    const token = new URLSearchParams(window.location.search).get("token")
    if (!token) return
    await LoginService.resetPassword({
      requestBody: { new_password: data.new_password, token: token },
    })
  }

  const mutation = useMutation({
    mutationFn: resetPassword,
    onSuccess: () => {
      showSuccessToast(t("resetPassword.successToast"))
      reset()
      navigate({ to: "/login" })
    },
    onError: (err: ApiError) => {
      handleError(err)
    },
  })

  const onSubmit: SubmitHandler<NewPasswordForm> = async (data) => {
    mutation.mutate(data)
  }

  return (
    <Box
      minH="100vh"
      position="relative"
      overflow="hidden"
      layerStyle="publicPage"
    >
      <Box
        position="absolute"
        top="-24"
        right="-20"
        w={{ base: "64", md: "88" }}
        h={{ base: "64", md: "88" }}
        layerStyle="publicGlowPrimary"
      />
      <Box
        position="absolute"
        top="20%"
        left="-20"
        w={{ base: "52", md: "68" }}
        h={{ base: "52", md: "68" }}
        layerStyle="publicGlowSecondary"
      />

      <Box position="fixed" top="1rem" right="1rem" zIndex={20}>
        <ChakraLink href={landingUrl}>
          <IconButton
            aria-label={t("shared.homeAriaLabel")}
            bg="ui.panel"
            color="ui.brandText"
            borderWidth="1px"
            borderColor="ui.brandBorderSoft"
            rounded="full"
            boxShadow="ui.panelSm"
            _hover={{ bg: "ui.brandSoft" }}
          >
            <Image
              src={SymbolLogo}
              alt={t("shared.homeImageAlt")}
              boxSize="5"
            />
          </IconButton>
        </ChakraLink>
      </Box>

      <Container
        minH="100vh"
        maxW={FORM_CONTAINER_MAX_W}
        display="flex"
        alignItems="center"
        justifyContent="center"
        position="relative"
      >
        <InsightCard
          as="form"
          onSubmit={handleSubmit(onSubmit)}
          w="full"
          minH={FORM_CARD_MIN_H}
          px={{ base: 7, md: 10 }}
          py={{ base: 8, md: 10 }}
          display="flex"
          flexDir="column"
          alignItems="center"
          justifyContent="center"
          gap={4}
          rounded="3xl"
        >
          <ThemeLogo
            height="auto"
            w={{ base: "368px", md: "416px" }}
            objectFit="contain"
            alignSelf="center"
            mb={4}
          />
          <Heading
            w={FORM_CONTROL_MAX_W}
            size="xl"
            color="ui.brandText"
            textAlign="center"
            mb={1}
          >
            {t("resetPassword.title")}
          </Heading>
          <Text w={FORM_CONTROL_MAX_W} textAlign="center" mb={1}>
            {t("resetPassword.description")}
          </Text>
          <Box w={FORM_CONTROL_MAX_W}>
            <PasswordInput
              startElement={<FiLock />}
              type="new_password"
              errors={errors}
              {...register(
                "new_password",
                newPasswordRules(true, {
                  required: t("validation.passwordRequired"),
                  length: t("validation.passwordLength"),
                  uppercase: t("validation.passwordUppercase"),
                  number: t("validation.passwordNumber"),
                  special: t("validation.passwordSpecial"),
                }),
              )}
              placeholder={t("password.newPlaceholder")}
              helperText={<PasswordRequirements password={newPasswordValue} />}
            />
          </Box>
          <Box w={FORM_CONTROL_MAX_W}>
            <PasswordInput
              startElement={<FiLock />}
              type="confirm_password"
              errors={errors}
              {...register(
                "confirm_password",
                confirmPasswordRules(getValues, true, {
                  mismatch: t("validation.passwordMismatch"),
                  required: t("validation.passwordConfirmationRequired"),
                }),
              )}
              placeholder={t("password.confirmPlaceholder")}
            />
          </Box>
          <Button
            w={FORM_CONTROL_MAX_W}
            layerStyle="brandGradientButton"
            type="submit"
          >
            {t("resetPassword.submit")}
          </Button>
        </InsightCard>
      </Container>
    </Box>
  )
}
