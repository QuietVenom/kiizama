import {
  Box,
  Link as ChakraLink,
  Container,
  Heading,
  IconButton,
  Image,
  Input,
  Text,
} from "@chakra-ui/react"
import { useMutation } from "@tanstack/react-query"
import { type SubmitHandler, useForm } from "react-hook-form"
import { useTranslation } from "react-i18next"
import { FiMail } from "react-icons/fi"

import { type ApiError, LoginService } from "@/client"
import InsightCard from "@/components/Common/InsightCard"
import ThemeLogo from "@/components/Common/ThemeLogo"
import { Button } from "@/components/ui/button"
import { Field } from "@/components/ui/field"
import { InputGroup } from "@/components/ui/input-group"
import useCustomToast from "@/hooks/useCustomToast"
import { buildEmailPattern, handleError } from "@/utils"
import SymbolLogo from "/assets/images/symbol.svg"

interface FormData {
  email: string
}

const FORM_CONTAINER_MAX_W = { base: "md", md: "3xl" } as const
const FORM_CARD_MIN_H = { base: "auto", md: "560px" } as const
const FORM_CONTROL_MAX_W = { base: "full", md: "50%" } as const

export function RecoverPasswordPage() {
  const { t } = useTranslation("auth")
  const landingUrl = "/"
  const {
    register,
    handleSubmit,
    reset,
    formState: { errors, isSubmitting },
  } = useForm<FormData>()
  const { showSuccessToast } = useCustomToast()

  const recoverPassword = async (data: FormData) => {
    await LoginService.recoverPassword({
      email: data.email,
    })
  }

  const mutation = useMutation({
    mutationFn: recoverPassword,
    onSuccess: () => {
      showSuccessToast(t("recoverPassword.successToast"))
      reset()
    },
    onError: (err: ApiError) => {
      handleError(err)
    },
  })

  const onSubmit: SubmitHandler<FormData> = async (data) => {
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
            {t("recoverPassword.title")}
          </Heading>
          <Text w={FORM_CONTROL_MAX_W} textAlign="center" mb={1}>
            {t("recoverPassword.description")}
          </Text>
          <Field
            w={FORM_CONTROL_MAX_W}
            invalid={!!errors.email}
            errorText={errors.email?.message}
          >
            <InputGroup w="100%" startElement={<FiMail />}>
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
          <Button
            w={FORM_CONTROL_MAX_W}
            layerStyle="brandGradientButton"
            type="submit"
            loading={isSubmitting}
          >
            {t("recoverPassword.submit")}
          </Button>
        </InsightCard>
      </Container>
    </Box>
  )
}
