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
import {
  createFileRoute,
  Link as RouterLink,
  redirect,
} from "@tanstack/react-router"
import { useState } from "react"
import { type SubmitHandler, useForm } from "react-hook-form"
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
import { ensureValidStoredSession } from "@/features/auth/session"
import useAuth from "@/hooks/useAuth"
import useCustomToast from "@/hooks/useCustomToast"
import { isPublicFeatureFlagEnabled } from "@/hooks/useFeatureFlags"
import { confirmPasswordRules, emailPattern, newPasswordRules } from "@/utils"
import SymbolLogo from "/assets/images/symbol.svg"

const FORM_CONTAINER_MAX_W = { base: "md", md: "3xl" } as const
const FORM_CARD_MIN_H = { base: "auto", md: "560px" } as const
const FORM_CONTROL_MAX_W = { base: "full", md: "50%" } as const
const WAITING_LIST_FLAG_KEY = "waiting-list"

export const Route = createFileRoute("/signup")({
  component: SignUp,
  beforeLoad: async () => {
    if (await ensureValidStoredSession()) {
      throw redirect({
        to: "/overview",
      })
    }

    let isWaitingListEnabled = false
    try {
      isWaitingListEnabled = await isPublicFeatureFlagEnabled(
        WAITING_LIST_FLAG_KEY,
      )
    } catch {
      // If flag fetch fails, keep signup available.
    }

    if (isWaitingListEnabled) {
      throw redirect({
        to: "/waiting-list",
      })
    }
  },
})

type UserRegisterForm = Omit<UserRegister, "legal_acceptances"> & {
  confirm_password: string
}

function SignUp() {
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
      showErrorToast(
        "Estamos cargando la documentación legal requerida. Intenta de nuevo.",
      )
      return
    }

    if (legalDocumentsQuery.isError || !hasRequiredLegalDocuments) {
      const errorMessage =
        legalDocumentsQuery.error instanceof Error
          ? legalDocumentsQuery.error.message
          : "No se pudo cargar la documentación legal requerida. Intenta de nuevo."
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
      showErrorToast(
        "No se pudo cargar la documentación legal requerida. Intenta de nuevo.",
      )
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
            aria-label="Go to landing page"
            bg="ui.panel"
            color="ui.brandText"
            borderWidth="1px"
            borderColor="ui.brandBorderSoft"
            rounded="full"
            boxShadow="ui.panelSm"
            _hover={{ bg: "ui.brandSoft" }}
          >
            <Image src={SymbolLogo} alt="Kiizama symbol" boxSize="5" />
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
                  required: "Full Name is required",
                })}
                placeholder="Full Name"
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
                  required: "Email is required",
                  pattern: emailPattern,
                })}
                placeholder="Email"
                type="email"
              />
            </InputGroup>
          </Field>
          <Box w={FORM_CONTROL_MAX_W}>
            <PasswordInput
              type="password"
              startElement={<FiLock />}
              {...register("password", newPasswordRules())}
              placeholder="Password"
              errors={errors}
              helperText={<PasswordRequirements password={passwordValue} />}
            />
          </Box>
          <Box w={FORM_CONTROL_MAX_W}>
            <PasswordInput
              type="confirm_password"
              startElement={<FiLock />}
              {...register("confirm_password", confirmPasswordRules(getValues))}
              placeholder="Confirm Password"
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
            Sign Up
          </Button>
          {legalDocumentsQuery.isError && (
            <Text w={FORM_CONTROL_MAX_W} textAlign="center" color="red.300">
              No se pudo cargar la documentación legal requerida. Intenta de
              nuevo para continuar.
            </Text>
          )}
          <Text w={FORM_CONTROL_MAX_W} textAlign="center">
            Already have an account?{" "}
            <RouterLink to="/login" className="main-link">
              Log In
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
            <DialogTitle>Antes de crear tu cuenta</DialogTitle>
          </DialogHeader>
          <DialogBody>
            <Text mb={5}>
              {legalDocuments?.simplified_notice ??
                "Para crear tu cuenta, necesitas leer y aceptar la documentación legal aplicable. Puedes revisar cada documento en una nueva pestaña antes de continuar."}
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
                    He leído y acepto el Aviso de Privacidad
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
                    Abrir Aviso de Privacidad
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
                    He leído y acepto los Términos y Condiciones
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
                    Abrir Términos y Condiciones
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
              Cancelar
            </Button>
            <Button
              layerStyle="brandGradientButton"
              onClick={handleConfirmLegalAcceptance}
              disabled={isLegalConfirmDisabled}
              loading={isSignupPending}
              data-testid="confirm-legal-acceptance"
            >
              Crear cuenta
            </Button>
          </DialogFooter>
        </DialogContent>
      </DialogRoot>
    </Box>
  )
}
