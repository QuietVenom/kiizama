import {
  Box,
  Link as ChakraLink,
  Container,
  IconButton,
  Image,
  Input,
  Text,
} from "@chakra-ui/react"
import { useQuery } from "@tanstack/react-query"
import { Link as RouterLink } from "@tanstack/react-router"
import { useState } from "react"
import { type SubmitHandler, useForm } from "react-hook-form"
import { useTranslation } from "react-i18next"
import { FiLock, FiUser } from "react-icons/fi"

import { PublicLegalDocumentsService, type UserRegister } from "@/client"
import InsightCard from "@/components/Common/InsightCard"
import ThemeLogo from "@/components/Common/ThemeLogo"
import { Button } from "@/components/ui/button"
import { Checkbox } from "@/components/ui/checkbox"
import {
  DialogBody,
  DialogCloseTrigger,
  DialogContent,
  DialogFooter,
  DialogHeader,
  DialogRoot,
  DialogTitle,
} from "@/components/ui/dialog"
import { Field } from "@/components/ui/field"
import { InputGroup } from "@/components/ui/input-group"
import { PasswordInput } from "@/components/ui/password-input"
import { PasswordRequirements } from "@/components/ui/password-requirements"
import useAuth from "@/hooks/useAuth"
import useCustomToast from "@/hooks/useCustomToast"
import {
  buildEmailPattern,
  confirmPasswordRules,
  newPasswordRules,
} from "@/utils"
import SymbolLogo from "/assets/images/symbol.svg"

const FORM_CONTAINER_MAX_W = { base: "md", md: "3xl" } as const
const FORM_CARD_MIN_H = { base: "auto", md: "560px" } as const
const FORM_CONTROL_MAX_W = { base: "full", md: "50%" } as const

type UserRegisterForm = Omit<UserRegister, "legal_acceptances"> & {
  confirm_password: string
}

export function SignUpPage() {
  const { t } = useTranslation("auth")
  const { signUpMutation } = useAuth()
  const { showErrorToast } = useCustomToast()
  const landingUrl = "/"
  const [isLegalModalOpen, setIsLegalModalOpen] = useState(false)
  const [pendingSignupData, setPendingSignupData] =
    useState<UserRegisterForm | null>(null)
  const [hasAcceptedPrivacyNotice, setHasAcceptedPrivacyNotice] =
    useState(false)
  const [hasAcceptedTermsConditions, setHasAcceptedTermsConditions] =
    useState(false)
  const {
    register,
    handleSubmit,
    getValues,
    watch,
    formState: { errors, isSubmitting },
  } = useForm<UserRegisterForm>({
    mode: "onBlur",
    criteriaMode: "all",
    defaultValues: {
      email: "",
      full_name: "",
      password: "",
      confirm_password: "",
    },
  })
  const legalDocumentsQuery = useQuery({
    queryKey: ["publicLegalDocuments"],
    queryFn: () => PublicLegalDocumentsService.listPublicLegalDocuments(),
    retry: false,
  })

  const legalDocuments = legalDocumentsQuery.data
  const privacyNoticeDocument = legalDocuments?.documents.find(
    (document) => document.type === "privacy_notice",
  )
  const termsConditionsDocument = legalDocuments?.documents.find(
    (document) => document.type === "terms_conditions",
  )
  const hasRequiredLegalDocuments = Boolean(
    legalDocuments && privacyNoticeDocument && termsConditionsDocument,
  )

  const resetLegalModalState = () => {
    setIsLegalModalOpen(false)
    setPendingSignupData(null)
    setHasAcceptedPrivacyNotice(false)
    setHasAcceptedTermsConditions(false)
  }

  const onSubmit: SubmitHandler<UserRegisterForm> = (data) => {
    if (legalDocumentsQuery.isPending) {
      showErrorToast(t("signup.legal.loadError"))
      return
    }

    if (legalDocumentsQuery.isError || !hasRequiredLegalDocuments) {
      const errorMessage =
        legalDocumentsQuery.error instanceof Error
          ? legalDocumentsQuery.error.message
          : t("signup.legal.loadError")
      showErrorToast(errorMessage)
      return
    }

    setPendingSignupData(data)
    setHasAcceptedPrivacyNotice(false)
    setHasAcceptedTermsConditions(false)
    setIsLegalModalOpen(true)
  }

  const handleConfirmLegalAcceptance = () => {
    if (
      !pendingSignupData ||
      !hasRequiredLegalDocuments ||
      !hasAcceptedPrivacyNotice ||
      !hasAcceptedTermsConditions
    ) {
      showErrorToast(t("signup.legal.loadError"))
      return
    }

    signUpMutation.mutate(
      {
        email: pendingSignupData.email,
        full_name: pendingSignupData.full_name,
        password: pendingSignupData.password,
        legal_acceptances: {
          privacy_notice: true,
          terms_conditions: true,
        },
      },
      {
        onSuccess: () => {
          resetLegalModalState()
        },
      },
    )
  }

  const passwordValue = watch("password")
  const isSignupPending = signUpMutation.isPending
  const isLegalConfirmDisabled =
    !hasAcceptedPrivacyNotice || !hasAcceptedTermsConditions || isSignupPending

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
          <Field
            w={FORM_CONTROL_MAX_W}
            invalid={!!errors.full_name}
            errorText={errors.full_name?.message}
          >
            <InputGroup w="100%" startElement={<FiUser />}>
              <Input
                minLength={3}
                {...register("full_name", {
                  required: t("validation.fullNameRequired"),
                })}
                placeholder={t("signup.fullNamePlaceholder")}
                type="text"
              />
            </InputGroup>
          </Field>

          <Field
            w={FORM_CONTROL_MAX_W}
            invalid={!!errors.email}
            errorText={errors.email?.message}
          >
            <InputGroup w="100%" startElement={<FiUser />}>
              <Input
                {...register("email", {
                  required: t("validation.emailRequired"),
                  pattern: buildEmailPattern(t("validation.invalidEmail")),
                })}
                placeholder={t("shared.emailPlaceholder")}
                type="email"
              />
            </InputGroup>
          </Field>
          <Box w={FORM_CONTROL_MAX_W}>
            <PasswordInput
              type="password"
              startElement={<FiLock />}
              {...register(
                "password",
                newPasswordRules(true, {
                  required: t("validation.passwordRequired"),
                  length: t("validation.passwordLength"),
                  uppercase: t("validation.passwordUppercase"),
                  number: t("validation.passwordNumber"),
                  special: t("validation.passwordSpecial"),
                }),
              )}
              placeholder={t("password.placeholder")}
              errors={errors}
              helperText={<PasswordRequirements password={passwordValue} />}
            />
          </Box>
          <Box w={FORM_CONTROL_MAX_W}>
            <PasswordInput
              type="confirm_password"
              startElement={<FiLock />}
              {...register(
                "confirm_password",
                confirmPasswordRules(getValues, true, {
                  mismatch: t("validation.passwordMismatch"),
                  required: t("validation.passwordConfirmationRequired"),
                }),
              )}
              placeholder={t("password.confirmPlaceholder")}
              errors={errors}
            />
          </Box>
          <Button
            w={FORM_CONTROL_MAX_W}
            layerStyle="brandGradientButton"
            type="submit"
            loading={isSignupPending || isSubmitting}
            disabled={isSignupPending}
          >
            {t("signup.submit")}
          </Button>
          {legalDocumentsQuery.isError && (
            <Text w={FORM_CONTROL_MAX_W} textAlign="center" color="red.300">
              {t("signup.legal.loadErrorInline")}
            </Text>
          )}
          <Text w={FORM_CONTROL_MAX_W} textAlign="center">
            {t("signup.alreadyHaveAccount")}{" "}
            <RouterLink to="/login" className="main-link">
              {t("signup.loginLink")}
            </RouterLink>
          </Text>
        </InsightCard>
      </Container>
      <DialogRoot
        open={isLegalModalOpen}
        onOpenChange={({ open }) => {
          if (!open && !isSignupPending) {
            resetLegalModalState()
          }
        }}
      >
        <DialogContent maxW="lg" data-testid="signup-legal-modal">
          {!isSignupPending && <DialogCloseTrigger />}
          <DialogHeader>
            <DialogTitle>{t("signup.legal.title")}</DialogTitle>
          </DialogHeader>
          <DialogBody>
            <Text mb={5}>
              {legalDocuments?.simplified_notice ??
                t("signup.legal.fallbackNotice")}
            </Text>
            <Box display="flex" flexDirection="column" gap={4}>
              {privacyNoticeDocument && (
                <Box>
                  <Checkbox
                    checked={hasAcceptedPrivacyNotice}
                    onCheckedChange={({ checked }) =>
                      setHasAcceptedPrivacyNotice(Boolean(checked))
                    }
                    data-testid="accept-privacy-checkbox"
                  >
                    {t("signup.legal.privacyAcceptance")}
                  </Checkbox>
                  <ChakraLink
                    href={privacyNoticeDocument.url}
                    target="_blank"
                    rel="noopener noreferrer"
                    textDecoration="underline"
                    fontSize="sm"
                    ms="7"
                    data-testid="privacy-link"
                  >
                    {t("signup.legal.privacyLink")}
                  </ChakraLink>
                </Box>
              )}
              {termsConditionsDocument && (
                <Box>
                  <Checkbox
                    checked={hasAcceptedTermsConditions}
                    onCheckedChange={({ checked }) =>
                      setHasAcceptedTermsConditions(Boolean(checked))
                    }
                    data-testid="accept-terms-checkbox"
                  >
                    {t("signup.legal.termsAcceptance")}
                  </Checkbox>
                  <ChakraLink
                    href={termsConditionsDocument.url}
                    target="_blank"
                    rel="noopener noreferrer"
                    textDecoration="underline"
                    fontSize="sm"
                    ms="7"
                    data-testid="terms-link"
                  >
                    {t("signup.legal.termsLink")}
                  </ChakraLink>
                </Box>
              )}
            </Box>
          </DialogBody>
          <DialogFooter gap={2}>
            <Button
              variant="subtle"
              colorPalette="gray"
              onClick={resetLegalModalState}
              disabled={isSignupPending}
            >
              {t("signup.legal.cancel")}
            </Button>
            <Button
              layerStyle="brandGradientButton"
              onClick={handleConfirmLegalAcceptance}
              disabled={isLegalConfirmDisabled}
              loading={isSignupPending}
              data-testid="confirm-legal-acceptance"
            >
              {t("signup.legal.confirm")}
            </Button>
          </DialogFooter>
        </DialogContent>
      </DialogRoot>
    </Box>
  )
}
